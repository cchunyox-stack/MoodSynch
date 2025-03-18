#function to preprocess readings
import numpy as np
import pandas as pd
import hrvanalysis
from hrvanalysis import get_time_domain_features, get_frequency_domain_features

def preprocess_IBI_intervals(ibi_intervals):
    time_domain_features = get_time_domain_features(ibi_intervals)
    frequency_domain_features = get_frequency_domain_features(ibi_intervals)

    #extracted_features = []

    user_features = pd.DataFrame({
        **time_domain_features,
        **frequency_domain_features
        }, index=[0])
    #extracted_features.append(user_features)

    return user_features
