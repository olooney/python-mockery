""" Mockery demonstrates using mocks for unit testing.

1) using the "mock" package to quickly mock up objects
2) patching mock objects into subject code
3) using the more specialized "betamax" package to mock requests.

mock was added to the standard library in Python 3.3 and is
available from pip for earlier versions. That means it is fully
supported by the core Python development team, not a "hack."

There are several very similar subclases of mock.Mock: mock.MagicMock,
mock.NonCallableMock, etc., but the differences are fairly small.
MagicMock is a good default choice because it support "magic methods"
like __str__ and __get__ out-of-the box.

>>> import mock
>>> mm = mock.MagicMock()

all mock.Mocks share two key behaviors. First, you can call any
property or call any function and not only will the call succeed,
it will return another mock.Mock object.

>>> mm.some_property_i_just_made_up
<MagicMock name='mock.some_property_i_just_made_up' id='...'>

>>> mm.whatever_method('with', 'any', args='you like')
<MagicMock name='mock.whatever_method()' id='...'>

Of course these can be chained:
>>> mm.items[0].name.startswith('My')
<MagicMock name='mock.items.__getitem__().name.startswith()' id='...'>

By itself, this wouldn't be very useful. But mocks aren't just allowing
arbitrary code to succeed; they are also carefully recording everything
that happens to them, and can be prepared with test data.

>>> mm.items.__len__.return_value = 3
>>> len(mm.items)
3
>>> mm.items.__len__.called
True
>>> mm.items.__len__.assert_called_once_with()

You should now be able to guess how mocks are used in unittesting.
When a subject library you want to test calls into control you don't
control and don't want to exercise, you can give it a mock object
instead. You prepare the mock object to respond as you'd expect the
real external library to, pass it into the subject code, and then
verify that it was called in the manner you expect.

"""
import mock
import unittest
from betamax import Betamax
import requests
import datetime
import real_code
import doctest

mock_requests = requests.Session()
# A Session can stand in for the whole "requests" module because the global
# requests functions (requests.get(), requests.post(), etc.) are really just
# convenience wrappers around an anonymous session. In fact, the "requests"
# module is duck-type isomorphic to the Session class.
#
# Note that even though it is named "mock_", it is not a mock.Mock object.
# Nevertheless, it fullfills the role of the Mock pattern in the below tests;
# there are lots of ways to "mock" something! Mock is merely a convenience.

class TestGoogleForToday(unittest.TestCase):
    """Test the real_code."""

    def test_format_date(self):
        """This test does not need any mocks or patches. The
        format_date_for_search() function is well-designed."""

        # closures can help you define a "mini-language" for writting clean,
        # readable tests when you have a lot of similar things to assert.
        def assert_format(date_tuple, required):
            date = datetime.date(*date_tuple)
            result = real_code.format_date_for_search(date)
            self.assertEqual(result, required)

        assert_format((2014, 1, 1), 'Wednesday January 1st 2014')
        assert_format((2014, 1, 2), 'Thursday January 2nd 2014')
        assert_format((2014, 1, 3), 'Friday January 3rd 2014')
        assert_format((2014, 1, 4), 'Saturday January 4th 2014')


    def test_format_date_with_mock(self):
        """When possible, always prefer to explicitly pass mock objects
        into the subject library."""

        # step #1: prepare the mock before the test
        mock_date = mock.Mock(spec=datetime.date)
        mock_date.strftime.return_value = 'Friday January 17th 2014'
        # to set properties, you need to grab the class of the mock.
        # (every mock object as it's own unique class.)
        mock_day_property = mock.PropertyMock(return_value=17)
        type(mock_date).day = mock_day_property

        # step #2: call into the subject code
        result = real_code.format_date_for_search(mock_date)
        self.assertEqual(result, 'Friday January 17th 2014')

        # step #3: validate the mocks were used as expected
        mock_day_property.assert_called_with()


    # with this patch in place, anytime any code in the "real_time"
    # module uses the "datetime" it imported, it will call into
    # our mock instead. The patch will expire at the end of the function.
    # (mock.patch is also a context manager, so you can use it in a "with"
    # block if you need more granular control. The autospec means that it
    # will recursively create mock objects with the same set of properties
    # and methods as what we're replacing, and these mock objects will
    # raise an exception if you use an unknown property. The recursion
    # is lazy so don't worry about undue performance considerations.
    @mock.patch('real_code.datetime', autospec=True)
    def test_format_today_for_search(self, mock_datetime):
        """This test needs a mock because the subject uses
        a varying, global resource (the today() constructor.)"""

        mock_datetime.date.today.return_value = datetime.date(2014, 1, 17)
        # note that by mocking out the datetime library, we're completely
        # taking over responsibility for playing the role of the whole
        # package. Luckily, we know that only that one function is called,
        # so this is relatively easy here. In other cases, we may have to
        # "side_effect" to leave other classes and functions in a working state.

        # this is the unit test code proper
        result = real_code.format_today_for_search()
        mock_datetime.date.today.assert_called_once_with()
        self.assertEqual(result, 'Friday January 17th 2014')


    # mock.patch replaces objects with mock.MagicMocks by default,
    # you can splice in whatever you want. To mock the requests library,
    # we're going to use a requests.Session instead.
    # note that you can "stack up" mock.patch decorators.
    @mock.patch('real_code.requests', new=mock_requests)
    @mock.patch('real_code.datetime', autospec=True)
    def test_google_for_today(self, mock_datetime):
        """Test the real service, using Betamax to "mock" out requests."""

        # mock out today(), same as before
        mock_datetime.date.today.return_value = datetime.date(2014, 1, 17)

        with Betamax(mock_requests,
                     cassette_library_dir='betamax_cassettes') as betamax:
            # The first time I ran this unit test, I set record to 'once' so
            # that it would create the cassette file and record the
            # request/response.  betamax.use_cassette('google', record='once')

            # After that, I set it to 'none' so that it would throw an error if
            # the request does not match a pre-recorded request. This prevents
            # it from ever even trying to  access the real network.
            betamax.use_cassette('google', record='none')

            urls = list(real_code.google_for_today())

            # generic tests that will always pass against live data
            self.assertEquals(len(urls), 10)
            for url in urls:
                self.assertTrue(url.startswith('http'))
                self.assertTrue('//' in url)

            # we can also write tests using specific knowledge of the test
            # fixtures, or in this case the recorded request.
            self.assertEquals(
                urls[0],
                "http://newday.blogs.cnn.com/2014/01/17/5-things-to-know-for-your-new-day-friday-january-17/")


def main():
    """run all the tests."""
    doctest.testmod(optionflags=doctest.ELLIPSIS)
    unittest.main()

if __name__ == '__main__':
    main()
