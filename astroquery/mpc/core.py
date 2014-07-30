# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import print_function

# put all imports organized as shown below
# 1. standard library imports
import warnings

# 2. third party imports

# 3. local imports - use relative imports
from ..query import QueryWithLogin, suspend_cache # inherits from BaseQuery as required
from ..utils import commons # has common functions required by most modules incl. TimeoutError
from ..utils import prepend_docstr_noreturns # automatically generate docs for similar functions
from ..utils import async_to_sync # all class methods must be callable as static as well as instance methods.
from . import SERVER, TIMEOUT, RETRIEVAL_TIMEOUT # configurable items declared in __init__.py

import requests

__author__ = 'Michele Bannister   git:@mtbannister'

"""
Queries should be POSTed to either minorplanetcenter.net/ws/orbits or minorplanetcenter.net/ws/observations.
The message header should include basic authorization -- username: mpc_ws and password: mpc!!ws
The header should also declare Content-Type: application/xml
The body of the message should contain the parameters, wrapped in xml, e.g.:
    <designation>2008 TC3</designation>

Just to get things started, the designation is the only parameter currently supported, and the only accessible tables
are orbits and observations.
The web service should return the orbit (or observations) for the designated object wrapped in an array in xml.
"""

# export all the public classes and methods
__all__ = ['Mpc']

# declare global variables and constants if any

@async_to_sync
class Mpc(QueryWithLogin):
    """
    Connects to the Minor Planet Center public-facing database and allows queries on specific objects.
    """
    # use the Configuration Items imported from __init__.py to set the URL, TIMEOUT, etc.
    SERVER_URL = SERVER.defaultvalue
    TIMEOUT = TIMEOUT.defaultvalue

    def __init__(self):
        super(Mpc, self).__init__()
        self.orbit = None
        self.observations = None

    def _login(self, username, password):
        self.username = username
        self.password = password
        return self.username, self.password

    def _validate_object_id(self, object_id):
        assert isinstance(object_id, str)
        object_id_type = {'name':None, "number":None, "designation":None}
        if object_id.isalpha():
            retval = "name"
        elif object_id.isalnum() and len(object_id) == 7:
            retval = 'designation'
        elif object_id.isdigit():
            retval = 'number'
        else:
            raise ValueError('%s unknown type: neither name, number nor provisional designation.' % object_id)

        return retval

    def query_object(self, object_id, get_query_payload=False, verbose=False):
        """
        Retrieve orbital elements and observations of the given object from the MPC.
        This implements the same as
        http://mpcdb1.cfa.harvard.edu/ws/search?number=134340&json=1
        for object (134340)

        Parameters
        ----------
        object_name : str
            name of the identifier to query.
        get_query_payload : bool, optional
            This should default to False. When set to `True` the method
            should return the HTTP request parameters as a dict.
        verbose : bool, optional
           This should default to `False`, when set to `True` it displays
           VOTable warnings.

        Returns
        -------
        result : `astropy.table.Table`
            The result of the query as an `astropy.table.Table` object.

        Examples
        --------
        While this section is optional you may put in some examples that
        show how to use the method. The examples are written similar to
        standard doctests in python.
        """

        # typically query_object should have the following steps:
        # 1. call the corresponding query_object_async method, and
        #    get the HTTP response of the query
        # 2. check if 'get_query_payload' is set to True, then
        #    simply return the dict of HTTP request parameters.
        # 3. otherwise call the parse_result method on the
        #    HTTP response returned by query_object_async and
        #    return the result parsed as astropy.Table
        # These steps are filled in below, but may be replaced
        # or modified as required.

        response = self.query_object_async(object_id, get_query_payload=get_query_payload)
        if get_query_payload:
            return response
        result = self._parse_result(response, verbose=verbose)
        return result

    # all query methods usually have a corresponding async method
    # that handles making the actual HTTP request and returns the
    # raw HTTP response, which should be parsed by a separate
    # parse_result method. Since these async counterparts take in
    # the same parameters as the corresponding query methods, but
    # differ only in the return value, they should be decorated with
    # prepend_docstr_noreturns which will automatically generate
    # the common docs. See below for an example.


    @prepend_docstr_noreturns(query_object.__doc__)
    def query_object_async(self, object_name, get_query_payload=False) :
        """
        Returns
        -------
        response : `requests.Response`
            The HTTP response returned from the service.
            All async methods should return the raw HTTP response.
        """
        # the async method should typically have the following steps:
        # 1. First construct the dictionary of the HTTP request params.
        # 2. If get_query_payload is `True` then simply return this dict.
        # 3. Else make the actual HTTP request and return the corresponding
        #    HTTP response
        # All HTTP requests are made via the `commons.send_request` method.
        # This uses the Python Requests library internally, and also takes
        # care of error handling.
        # See below for an example:

        # first initialize the dictionary of HTTP request parameters
        request_payload = self._args_to_payload(object_name)

        if get_query_payload:
            return request_payload
        # commons.send_request takes 4 parameters - the URL to query, the dict of
        # HTTP request parameters we constructed above, the TIMEOUT which we imported
        # from __init__.py and the type of HTTP request - either 'GET' or 'POST'.
        obs_response = commons.send_request(self.SERVER_URL,
                                        request_payload,
                                        self.TIMEOUT,
                                        request_type='POST',
                                        auth = (self.username, self.password))

        return obs_response  # currently a requests.models.Response

    def _args_to_payload(self, object_id, return_request=None):
        payload = dict()
        # Here the dictionary key should match
        # the exact parameter name as expected by the remote server. The
        # corresponding dict value should also be in the same format as
        # expected by the server.

        oID = object_id.strip()
        object_id_type = self._validate_object_id(oID)
        payload[object_id_type] = oID
        if return_request:
            payload['return'] = return_request
        payload['json'] = '1'  # ensures results are in JSON rather than xml

        return payload

    def _parse_result(self, response, verbose=False):
        """
        Parses the results from the HTTP response to `astropy.table.Table`.
        This is currently expecting _args_to_payload() to have set the return type to JSON.

        Parameters
        ----------
        response : `requests.Response`
            The HTTP response object
        verbose : bool, optional
            Defaults to false. When true it will display warnings whenever the JSON
            returned from the MPC doesn't conform to the standard.

        Returns
        -------
        table : `astropy.table.Table`
        """
        if not verbose:
            commons.suppress_vo_warnings()

        retval = response.json()[0]['properties']
        print retval
        # Check if table is empty
        if len(retval.keys()) == 0:
            warnings.warn("Query returned no results, so the table will be empty")

        return retval


    def query_orbital_elements(self, elements, get_query_payload=False, verbose=False):
        """
        Search based on eccentricity, orbital major axis,
        or some other parameter that is likely to be catalogued (accurately?).
        """
        raise NotImplementedError

    def query_observations(self, name, get_query_payload=False, verbose=False):
        """
        e.g. http://mpcdb1.cfa.harvard.edu/ws/observations?number=134340&json=1
        :param name: Object name (e.g. Eris) or designation (134340 or 2010 VW93)
        :param get_query_payload:
        :param verbose:
        :return:
        """


# the default tool for users to interact with is an instance of the Class
mpc_instance = Mpc()

# once your class is done, tests should be written
# See ./tests for examples on this

# Next you should write the docs in astroquery/docs/module_name
# using Sphinx.


