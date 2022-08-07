# Zoopla Fetcher

Get ALL the listing details from Zoopla. Returns the following per listing:

listingId, 
acorn, 
acornType, 
areaName, 
bedsMax, 
bedsMin, 
branchId, 
branchLogoUrl, 
branchName, 
brandName, 
chainFree, 
companyId, 
countryCode, 
countyAreaName, 
currencyCode, 
displayAddress, 
furnishedState, 
groupId, 
hasEpc, 
hasFloorplan, 
incode, 
isRetirementHome, 
isSharedOwnership, 
listingCondition, 
listingsCategory, 
listingStatus, 
location, 
memberType, 
numBaths, 
numBeds, 
numImages, 
numRecepts, 
outcode, 
postalArea, 
postTownName, 
priceActual, 
price, 
priceMax, 
priceMin, 
priceQualifier, 
propertyHighlight, 
propertyType, 
regionName, 
section, 
sizeSqFeet, 
tenure, 
zindex, 
national_rail_station, 
national_rail_station_distance_miles, 
uk_school_primary, 
uk_school_primary_distance_miles, 
uk_school_secondary, 
uk_school_secondary_distance_miles, 
detailedDescription, 
latitude, 
longitude, 
first_listed,
total_sq_footage,
number_of_price_changes, 
avg_pct_per_price_change, 
max_pct_per_price_change, 
min_pct_per_price_change, 
uk_school_primary_and_secondary, 
uk_school_primary_and_secondary_distance_miles

### Square footage

The code also parses the floorplan images, and extracts out the total square footage of the properties. This is the `total_sq_footage` field in the output.
The accuracy is highly dependent on the quality of the floorplan, if it has grainy text, the parsing will not work so well


# Run

### Query all details

An example query script is available in `zoopla_fetcher/scripts/example_query.py`

```python

from zoopla_fetcher.listings_query import ListingsQuery

# Set up query
prop_query = ListingsQuery(query_string="SW11",
                           radius_miles=0.5,
                           beds_min=2,
                           beds_max=4)
all_properties = prop_query.extract_all_properties_details(threads=8)
# Save output
all_properties.to_excel("example_query.xlsx")
```

### Get all price change history
```python
price_history = prop_query.extract_all_properties_price_history(threads=8)
# Save output
price_history.to_excel("example_query_price_history.xlsx")
```




