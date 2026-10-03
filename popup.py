#!/usr/bin/env python3
"""Standalone AppKit popup — launched as a subprocess by app.py."""
import argparse
import os

import AppKit
import objc
from Foundation import NSObject, NSTimer, NSMakeRect

WIN_W          = 640
WIN_H          = 520
IMG_H          = 300
STICKER_SIZE   = 150
AUTO_CLOSE_SECS = 30
PHRASE         = "I WILL LOCK IN"


def cleanup_image(path: str):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


def _lbl(text, font, color, bg, x, y, w, h):
    f = AppKit.NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    f.setStringValue_(text)
    f.setFont_(font)
    f.setTextColor_(color)
    f.setBackgroundColor_(bg)
    f.setDrawsBackground_(True)
    f.setBezeled_(False)
    f.setEditable_(False)
    f.setSelectable_(False)
    f.setAlignment_(AppKit.NSTextAlignmentCenter)
    return f


class PopupDelegate(NSObject):
    def init(self):
        self = objc.super(PopupDelegate, self).init()
        self._args = None
        self._window = None
        self._input_field = None
        self._cd_label = None
        self._remaining = AUTO_CLOSE_SECS
        self._timer = None
        self._closing = False
        return self

    def applicationDidFinishLaunching_(self, _notif):
        red   = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.902, 0.224, 0.275, 1.0)
        white = AppKit.NSColor.whiteColor()
        gray  = AppKit.NSColor.colorWithWhite_alpha_(0.533, 1.0)
        black = AppKit.NSColor.blackColor()
        dark  = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.067, 0.067, 0.067, 1.0)

        screen = AppKit.NSScreen.mainScreen()
        sw = screen.frame().size.width
        sh = screen.frame().size.height

        win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect((sw - WIN_W) / 2, (sh - WIN_H) / 2, WIN_W, WIN_H),
            AppKit.NSWindowStyleMaskTitled | AppKit.NSWindowStyleMaskClosable,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        win.setTitle_("LOCK IN POLICE")
        win.setLevel_(AppKit.NSFloatingWindowLevel)
        win.setBackgroundColor_(black)
        win.setCollectionBehavior_(AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces)
        win.setDelegate_(self)
        self._window = win

        cv = win.contentView()
        cv.setWantsLayer_(True)
        cv.layer().setBackgroundColor_(black.CGColor())

        args = self._args

        if args.mode == "image" and args.image_path:
            # ── Pexels image popup (unchanged layout) ──────────────────────
            try:
                img = AppKit.NSImage.alloc().initWithContentsOfFile_(args.image_path)
                if img:
                    iv = AppKit.NSImageView.alloc().initWithFrame_(
                        NSMakeRect(0, WIN_H - IMG_H, WIN_W, IMG_H)
                    )
                    iv.setImage_(img)
                    iv.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
                    cv.addSubview_(iv)
            except Exception:
                pass
            dismiss_y = 110

        else:
            # ── Quote popup ────────────────────────────────────────────────
            has_sticker = bool(getattr(args, "sticker_path", None))
            if has_sticker:
                # Animated GIF sticker centered near top
                sticker_x = (WIN_W - STICKER_SIZE) // 2
                sticker_y = WIN_H - STICKER_SIZE - 20
                try:
                    gif = AppKit.NSImage.alloc().initWithContentsOfFile_(args.sticker_path)
                    if gif:
                        iv = AppKit.NSImageView.alloc().initWithFrame_(
                            NSMakeRect(sticker_x, sticker_y, STICKER_SIZE, STICKER_SIZE)
                        )
                        iv.setImage_(gif)
                        iv.setAnimates_(True)
                        iv.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
                        cv.addSubview_(iv)
                except Exception:
                    pass
                hl_y = sticker_y - 75
                hl_font_size = 40
            else:
                hl_y = 320
                hl_font_size = 52

            cv.addSubview_(_lbl(
                args.headline,
                AppKit.NSFont.boldSystemFontOfSize_(hl_font_size), red, black,
                20, hl_y, WIN_W - 40, 70,
            ))
            dismiss_y = 160
            if args.subtext:
                cv.addSubview_(_lbl(
                    args.subtext,
                    AppKit.NSFont.systemFontOfSize_(20), white, black,
                    20, hl_y - 45, WIN_W - 40, 38,
                ))
                dismiss_y = 120

        # ── Dismiss section ────────────────────────────────────────────────
        if not args.no_dismiss:
            cv.addSubview_(_lbl(
                f'TYPE  "{PHRASE}"  TO DISMISS',
                AppKit.NSFont.boldSystemFontOfSize_(13), red, black,
                20, dismiss_y + 52, WIN_W - 40, 22,
            ))
            field = AppKit.NSTextField.alloc().initWithFrame_(
                NSMakeRect(80, dismiss_y, WIN_W - 160, 42)
            )
            field.setFont_(AppKit.NSFont.systemFontOfSize_(18))
            field.setTextColor_(white)
            field.setBackgroundColor_(dark)
            field.setBezeled_(True)
            field.setEditable_(True)
            field.setAlignment_(AppKit.NSTextAlignmentCenter)
            field.setDelegate_(self)
            cv.addSubview_(field)
            self._input_field = field
            win.makeFirstResponder_(field)

        # ── Countdown ──────────────────────────────────────────────────────
        cd = _lbl(
            f"Closing in: {AUTO_CLOSE_SECS}s",
            AppKit.NSFont.systemFontOfSize_(11), gray, black,
            20, 10, WIN_W - 40, 22,
        )
        cv.addSubview_(cd)
        self._cd_label = cd

        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self, "tick:", None, True
        )

        win.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)

    def tick_(self, _timer):
        self._remaining -= 1
        if self._cd_label:
            self._cd_label.setStringValue_(f"Closing in: {self._remaining}s")
        if self._remaining <= 0:
            self._close()

    def controlTextDidChange_(self, _notif):
        if self._input_field:
            if self._input_field.stringValue().strip().upper() == PHRASE:
                self._close()

    def windowWillClose_(self, _notif):
        self._close()

    @objc.python_method
    def _close(self):
        if self._closing:
            return
        self._closing = True
        if self._timer:
            self._timer.invalidate()
            self._timer = None
        if self._args and self._args.mode == "image":
            cleanup_image(self._args.image_path)
        AppKit.NSApp.terminate_(None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["image", "quote"], required=True)
    parser.add_argument("--image-path",   default="")
    parser.add_argument("--headline",     default="GET BACK TO WORK")
    parser.add_argument("--subtext",      default="")
    parser.add_argument("--sticker-path", default="")
    parser.add_argument("--no-dismiss",   action="store_true", default=False)
    args = parser.parse_args()

    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)

    delegate = PopupDelegate.alloc().init()
    delegate._args = args
    app.setDelegate_(delegate)

    app.run()


if __name__ == "__main__":
    main()
