"""Retired entry point: peripheral QFN vias must stay outside solderable pads."""

if __name__ == "__main__":
    raise SystemExit(
        "Peripheral via-in-pad insertion is retired. Use short external fanouts "
        "and run DRC plus verify_design.py. Only the 11 documented thermal vias "
        "retain filled/capped processing."
    )
