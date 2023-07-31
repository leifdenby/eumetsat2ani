def optional_debugging(with_debugger):
    """
    Optionally catch exceptions and launch ipdb
    """
    if with_debugger:
        import ipdb

        return ipdb.launch_ipdb_on_exception()
    else:

        class NoDebug:
            def __enter__(self):
                pass

            def __exit__(self, *args, **kwargs):
                pass

        return NoDebug()