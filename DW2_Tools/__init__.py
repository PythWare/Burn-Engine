"""
Burn Engine DW2 toolkit
"""
def __getattr__(name):
    if name == "Core_Tools":
        from .gui import Core_Tools
        return Core_Tools
    raise AttributeError(f"module 'DW2_Tools' has no attribute {name!r}")
