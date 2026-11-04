"""Nonactivating raw-script entry for the stopped service resource adapter.

An authenticated, externally admitted activation gate is not implemented yet.
Arguments, environment flags and caller-created receipts grant no authority.
Do not import runtime modules or perform filesystem/database/process actions.
"""


def main():
    print('BLOCKED_ACTIVATION_NOT_IMPLEMENTED')
    return 78


if __name__ == '__main__':
    raise SystemExit(main())
