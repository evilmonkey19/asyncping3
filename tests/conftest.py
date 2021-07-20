import pytest
from functools import partial

@pytest.fixture(autouse=True)
def patcher(request):
	from unittest import TestCase as t
	c = request.instance
	for k in dir(t):
		if hasattr(c,k):
			continue
		f = getattr(t,k)
		if callable(f):
			f = partial(f,c)
		setattr(c,k,f)
	t.__init__(c)
