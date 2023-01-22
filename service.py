if __name__ == '__main__':
    import sys

    sys.modules['_asyncio'] = None
    from lib.service.entrypoint import main

    main(sys.argv)
