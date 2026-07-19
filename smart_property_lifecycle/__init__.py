# -*- coding: utf-8 -*-
"""
Smart Property Lifecycle Suite - Main module initialization
"""

from . import models
from . import controllers
from . import wizards
from . import reports

def post_load():
    """Post-load hook for module initialization"""
    pass