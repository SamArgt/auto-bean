"""Run bundled stdlib helpers without installing an auto-bean Python package."""

from auto_bean.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
