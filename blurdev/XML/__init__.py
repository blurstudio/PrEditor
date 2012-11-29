"""
.. warning::

   Since Python 2.5, the python standard library has provided a very powerful 
   and fast XML reading and writing interface very similar to this 
   blurdev module -- `ElementTree <http://docs.python.org/library/xml.etree.elementtree.html>`_.
   
   Only use this module if you are updating an existing tool or library that 
   uses it or if it is part of a larger blur system that uses it, or if you 
   absolutely need the Qt type casting (though ideally that functionality 
   would be provided separately using composition, making use of the 
   standard library much easier). 
   
   If you are creating a new tool or library, consider using the 
   ElementTree module in the standard library instead.  
   
.. deprecated:: 2.0


The blurdev XML module is a convenience module that wraps python's minidom
implementation for XML reading and writing.  It also provides some automatic
type conversion to and from Qt types.

The blurdev XML module defines two classes -- :class:`XMLElement` and 
:class:`XMLDocument`


.. autoclass:: XMLElement
   :members:
   :undoc-members:
   
   
.. autoclass:: XMLDocument
   :members:
   :undoc-members:   

"""

from xmlelement import XMLElement
from xmldocument import XMLDocument


def __dict_replace(s, d):
    """Replace substrings of a string using a dictionary."""
    for key, value in d.items():
        s = s.replace(key, value)
    return s


def escape(data, entities={}):
    """Escape &, <, and > in a string of data.

    You can escape other strings of data by passing a dictionary as
    the optional entities parameter.  The keys and values must all be
    strings; each key will be replaced with its corresponding value.
    """

    # must do ampersand first
    data = data.replace("&", "&amp;")
    data = data.replace(">", "&gt;")
    data = data.replace("<", "&lt;")
    if entities:
        data = __dict_replace(data, entities)
    return data


def unescape(data, entities={}):
    """Unescape &amp;, &lt;, and &gt; in a string of data.

    You can unescape other strings of data by passing a dictionary as
    the optional entities parameter.  The keys and values must all be
    strings; each key will be replaced with its corresponding value.
    """
    data = data.replace("&lt;", "<")
    data = data.replace("&gt;", ">")
    if entities:
        data = __dict_replace(data, entities)
    # must do ampersand last
    return data.replace("&amp;", "&")
