from __future__ import unicode_literals

import pytest
from pyout.interface import Writer


@pytest.mark.parametrize("attr", ["_stream", "_content"])
def test_writer_required_attributes(attr):
    class Child(Writer):
        pass

    setattr(Child, attr, "anything")
    with pytest.raises(NotImplementedError):
        Child()
