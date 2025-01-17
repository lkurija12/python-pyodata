"""OData Client Implementation"""

import logging
import warnings

import pyodata.v2.model
import pyodata.v2.service
from pyodata.exceptions import PyODataException, HttpError


def _fetch_metadata(connection, url, logger):
    # download metadata
    logger.info('Fetching metadata')
    resp = connection.get(url + '$metadata')

    logger.debug('Retrieved the response:\n%s\n%s',
                 '\n'.join((f'H: {key}: {value}' for key, value in resp.headers.items())),
                 resp.content)

    if resp.status_code != 200:
        raise HttpError(
            f'Metadata request failed, status code: {resp.status_code}, body:\n{resp.content}', resp)

    mime_type = resp.headers['content-type']
    if not any((typ in ['application/xml', 'text/xml'] for typ in mime_type.split(';'))):
        raise HttpError(
            f'Metadata request did not return XML, MIME type: {mime_type}, body:\n{resp.content}',
            resp)

    return resp.content


class Client:
    """OData service client"""

    # pylint: disable=too-few-public-methods

    ODATA_VERSION_2 = 2

    def __new__(cls, url, connection, odata_version=ODATA_VERSION_2, namespaces=None,
                config: pyodata.v2.model.Config = None, metadata: str = None):
        """Create instance of the OData Client for given URL"""

        logger = logging.getLogger('pyodata.client')

        if odata_version == Client.ODATA_VERSION_2:

            # sanitize url
            url = url.rstrip('/') + '/'

            if metadata is None:
                metadata = _fetch_metadata(connection, url, logger)
            else:
                logger.info('Using static metadata')

            if config is not None and namespaces is not None:
                raise PyODataException('You cannot pass namespaces and config at the same time')

            if config is None:
                config = pyodata.v2.model.Config()

            if namespaces is not None:
                warnings.warn("Passing namespaces directly is deprecated. Use class Config instead", DeprecationWarning)
                config.namespaces = namespaces

            # create model instance from received metadata
            logger.info('Creating OData Schema (version: %d)', odata_version)
            schema = pyodata.v2.model.MetadataBuilder(metadata, config=config).build()

            # create service instance based on model we have
            logger.info('Creating OData Service (version: %d)', odata_version)
            service = pyodata.v2.service.Service(url, schema, connection, config=config)

            return service

        raise PyODataException(f'No implementation for selected odata version {odata_version}')
