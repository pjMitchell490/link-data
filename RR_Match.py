#!/usr/bin/env python
# coding: utf-8

# # Match Rural Routes to Wells

# ## Confidence Codes

# ## Import necessary libraries

# In[12]:


import pandas as pd
import geopandas as gpd
import configparser
from pathlib import Path
import re


# ## Import Parcels, Wells

# ## Read Config File

# In[13]:


# Config file contains file paths and name of township (uesd to match parcel TWP_CITY column)
config = configparser.ConfigParser()

#Change this path to the location of your own config.ini file
config.read('/home/petermitchell/Documents/ContractWork/config.ini')
config.sections()

twp = config['DEFAULT']['township']
verified_wells_path = config['DEFAULT']['verified_wells']
unverified_wells_path = config['DEFAULT']['unverified_wells']
parcels_path = config['DEFAULT']['parcels']
samples_path = config['DEFAULT']['samples']
output_path = config['DEFAULT']['output']

output_dir = Path(output_path)
output_dir.mkdir(parents=True, exist_ok=True)


# In[14]:


parcels = gpd.read_file(parcels_path)
# Limit parcels to just those in the desired township
#twp_parcels = parcels[parcels['TWP_CITY'] == twp]

parcels['Parcel_Township'] = parcels['TWP_CITY'].str.removesuffix(' TOWNSHIP')

verified_wells = gpd.read_file(verified_wells_path)
unverified_wells = gpd.read_file(unverified_wells_path)

verified_wells['Verified'] = True
unverified_wells['Verified'] = False

# Join verified and unverified wells into a single dataframe
wells = gpd.GeoDataFrame(pd.concat([verified_wells, unverified_wells], ignore_index=True))

# Export all wells
wells.to_file(output_dir / "wells.gpkg")


# ## Import Samples file as Pandas dataframe

# In[ ]:


samples = pd.read_csv(samples_path)

# Create new column with rural route addresses stripped of city and ZIP
rr_addresses = []
for value in samples['SampleAddress']:
    match = re.search('R[RT]\s\d*\sBOX\s\d*', value)
    rr_addresses.append(match if match is None else match.group())
samples['rr_addresses'] = rr_addresses

print(len(samples), "samples provided")
print(samples['rr_addresses'].count(), "samples have valid RR address")


# ## Match Rural Routes to Parcels

# In[ ]:


# Address_1 field in parcels contains the RR address

# Join on ADDRESS_1, rr_addresses

located_samples = parcels.merge(samples.dropna(subset='rr_addresses'), left_on='ADDRESS_1', right_on='rr_addresses')
located_samples = located_samples[located_samples['Parcel_Township'] == located_samples['Township']]

print(len(located_samples), "samples match at least one parcel")

# Set the right coordinate system (NAD27 UTM 15N, EPSG 26915)
located_samples = located_samples.to_crs(26915)
located_samples.to_file(output_dir / 'located_many.gpkg')

# Remove uncessary columns, drop cases where multiple parcels have the same RR address
located_samples = located_samples[['Lab_SampleID', 'rr_addresses', 'ADDRESS_1', 'geometry', 'Parcel_Township']].drop_duplicates(subset='Lab_SampleID', keep=False)


print(len(located_samples), "samples match exactly one parcel")




# ## Check for matching well

# In[ ]:


sample_well_match = gpd.sjoin(located_samples, wells, how="inner", predicate="intersects")
#print(sample_well_match.length)
sample_well_match.to_file(output_dir / 'sample_well_match.gpkg')

# Drop rows where the year sampled is before the year drilled
# unknown drill dates have a value of '0' and therefore survive this check
sample_well_match = sample_well_match[sample_well_match['Lab_SampleID'].str.slice(0,4) >= sample_well_match['DATE_DRLL'].astype(str).str.slice(0,4)]

# Filter to only necessary columns and remove cases where there are multiple wells on a parcel
unique_sample_well_match = sample_well_match[['Lab_SampleID', 'rr_addresses', 'UTME', 'UTMN', 'WELLID', 'Verified', 'DATE_DRLL', 'geometry']].drop_duplicates(subset='Lab_SampleID', keep=False)


# In[31]:


'''
CONFIDENCE CODES:
0: 
1:
2:
3:
4:
'''

#sample_confidence_codes = []
#for value in unique_sample_well_match['DATE_DRLL']:
#    if(value = 0)


# In[ ]:


unique_sample_well_match.to_file(output_dir / 'unique_sample_well_match.gpkg')
unique_sample_well_match.to_csv(output_dir / 'unique_sample_well_match.csv')

print("Matches with at least one well:", len(sample_well_match))
print("Matches with exactly one well:", len(unique_sample_well_match))


# In[7]:


located_samples.to_file(output_dir / 'located_samples.gpkg')

