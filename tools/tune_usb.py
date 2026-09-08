"""Retired entry point: USB Full-Speed routing no longer uses length-tuning loops."""

if __name__ == "__main__":
    raise SystemExit(
        "USB serpentine tuning is retired. Keep the short, parallel USB trunk; "
        "do not add length solely to compensate for the remaining small mismatch."
    )
