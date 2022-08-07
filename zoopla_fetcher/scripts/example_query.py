from zoopla_fetcher.listings_query import ListingsQuery
from zoopla_fetcher.config import log_config
import logging

_logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Initialise logging
    log_config.init_stream_logger(level=logging.INFO)

    # Set up query params
    prop_query = ListingsQuery(query_string="SW11",
                               radius_miles=0,
                               beds_min=2,
                               beds_max=4)
    _logger.info("Extracting all property details...")
    all_properties = prop_query.extract_all_properties_details(threads=8)
    # Save output
    all_properties.to_excel("sw11.xlsx")
