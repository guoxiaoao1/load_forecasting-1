import os
import itertools
import datetime

import tables as h5
import pandas as pd
import numpy as np

from sg.globals import SG_DATA_PATH

DATA_DIR = os.path.join(SG_DATA_PATH, "sintef/")
DATA_WITHOUT_DUPES_PATH = os.path.join(DATA_DIR, "eb_without_duplicates.blosc-9.h5")

class UserLoads(object):
    """This class reads an HDF5 file with per-user load values, and presents
    them in a dict-style to the user. Late loading, so values are not read
    until they are requested the first time.

    The set of user IDs can be accessed via the read-only property user_ids.
    """

    def __init__(self, path):
        """Open the file given in path, and read user IDs."""
        self._path = path
        self._store = pd.HDFStore(path, "r")
        self._user_ids = self._load_user_ids()
        self._loads = dict()

    def __del__(self):
        self._store.close()

    def _load_user_ids(self):
        # Could also user self._store.keys(), but this would return strings of
        # the form "id_nnnnn".
        return set(self._store["user_ids"])

    def close(self): 
        """Close the underlying HDF5 file, so it can be accessed by other
        functions. Any subsequent attempts to read from the file will fail."""
        self._store.close()
        
    def __len__(self):
        return len(self.user_ids)

    def read(self, user_id):
        """Read load data for user_id from HDF5 storage. Any existing data will
        be overwritten by data read from file. Use the subscript operator to
        access the loads rather than calling this function. Only call this
        function when you want to reset a modified load value to the value on
        file."""
        if not user_id in self.user_ids:
            raise KeyError("Invalid user ID. Check the read-only property " \
                           "user_ids for a list of valid IDs.")
        user_load = self._store["id_" + str(user_id)]
        self._loads[user_id] = user_load
        return user_load

    def read_all(self):
        """Read all load values from file at once. Normally late reading
        through the subscript operator is preferrable, but this function can be
        used for timing purposes or when manipulating the data
        interactively."""
        for user_id in self.user_ids:
            self.read(user_id)

    def __getitem__(self, user_id):
        if not user_id in self._loads:
            return self.read(user_id)
        return self._loads[user_id]

    def __setitem__(self, user_id, user_load):
        """Set new load values for user_id. The ID must correspond to an ID
        existing in the HDF5 file. The new load will not be written back to the
        HDF5 file, and will be overwritten by a subsequent call to read or
        read_all."""
        if not user_id in self.user_ids:
            raise KeyError("Invalid user ID. Check the read-only property " \
                           "user_ids for a list of valid IDs.")
        self._loads[user_id] = user_load

    def pop(self, user_id):
        """Remove specified loads and return them. Similar to dict.pop, but
        will not remove user_id from self.user_ids."""
        if not user_id in self.user_ids:
            raise KeyError("Invalid user ID. Check the read-only property " \
                           "user_ids for a list of valid IDs.")
        if not user_id in self.loads:
            self.read(user_id)
        return self._loads.pop(user_id)

    @property
    def user_ids(self):
        """The set of user IDs for which load data are stored in the HDF5
        file. This is a read-only property."""
        return list(self._user_ids)
    
    @property
    def loads(self):
        """A dict containing all the loads that have been read so far. This is
        a read-only property, but changing its contents will affect the
        internal representation in this class as well."""
        return self._loads

    @property
    def path(self):
        """Path to the HDF5 file as given to the __init__ function."""
        return self._path

    def __contains__(self, user_id):
        return user_id in self.user_id

    def __str__(self):
        return self.user_ids.__str__() + self.loads.__str__()


def experiment_periods():
    """Return the two preselected periods for which experiments will be carried
    out. These correspond to the two longest periods for which we have
    consecutive load values for an acceptable number of meters on the feeder
    with temperature recordings. Note that the temperature reading start
    later."""
    # Temperature readings start March 22 2004, loads start Feb 01 2004.
    # period1_start = pd.Period("2004-02-01 00:00", "H")
    # period1_end = pd.Period("2005-07-01 00:00", "H")
    # period2_start = pd.Period("2005-10-01 00:00", "H")
    # period2_end = pd.Period("2006-10-01 00:00", "H")
    period1_start = datetime.datetime.strptime("2004-02-01 00:00", "%Y-%m-%d %H:%M")
    period1_end = datetime.datetime.strptime("2005-07-01 00:00", "%Y-%m-%d %H:%M")
    period2_start = datetime.datetime.strptime("2005-10-01 00:00", "%Y-%m-%d %H:%M")
    period2_end = datetime.datetime.strptime("2006-10-01 00:00", "%Y-%m-%d %H:%M")
    return ((period1_start, period1_end), (period2_start, period2_end))
    
def manually_screened_ids():
    """IDs of meters that passed the automated tests for resolution, missing
    data, etc, but whose data do still not meet our criteria. These include:
       * Meters with 1kWh/h resolution that somehow passed the resolution test,
         e.g. by installing new meters at some point during the experiment
         period
       * Meters with missing data that have been processed and set to 0 by the
         utility company (as indicated by the status tag)
    The list does NOT include meters that have "weird" timeseries.
    """
    # These have no meaning here.
    # low_resolution_meters = (35466301, 82218621, 15720078, 80690326, 65630886, 
    #                          13824685, 87785213, 12645122, 89454871)
    # missing_data = (73122950, 39281849, 99260911, 92959456, 79042288, 97564405,
    #                 8751522)
    # return set(itertools.chain(low_resolution_meters, missing_data))
    return False

class UserLoads_Experiment(UserLoads):
    def _load_user_ids(self):
        return set(self._store['user_ids_cln_pred_exp'])
    
# The actual data sets
_tempfeeder_dup = None
_tempfeeder_nodup = None
_tempfeeder_exp = None

def tempfeeder_nodup():
    """Return userloads from the feeder that has temperature readings. Returns
    a time series where duplicates in the original files have been eliminated,
    keeping only the first value that was encountered during processing."""
    global _tempfeeder_nodup
    if _tempfeeder_nodup is None:
        _tempfeeder_nodup = UserLoads(DATA_WITHOUT_DUPES_PATH)
    return _tempfeeder_nodup

def tempfeeder_exp():
    """Return userloads from the feeder that has temperature readings. Returns
    a time series where duplicates in the original files have been eliminated,
    keeping only the first value that was encountered during processing.

    The list of user ids contains only those users/meters that have been
    selected for further processing as described in the EnergyCon paper.
    """
    global _tempfeeder_exp
    if _tempfeeder_exp is None:
        _tempfeeder_exp = UserLoads_Experiment(DATA_WITHOUT_DUPES_PATH)
    return _tempfeeder_exp

def tempfeeder_exp_nonzerotest_users():
    """Returns a list of user IDs that does not have a zero reading in the test period,
    which is from 2005-10-01 00:00 -> 2006-10-01 00:00. This selection is made so a
    MAPE (although somewhat useless nonetheless, since the values are so small)
    can be calculated."""

    return [ user for user in tempfeeder_exp().user_ids if all(tempfeeder_exp()[user]['Load']['2005-10-01 00:00':]) ]

def total_load(userloads, user_ids, period):
    """Calculate the total load for the given users period."""
    series = [userloads[user][period[0]:period[1]] for user in user_ids]
    total = series[0].copy()
    for single_series in series[1:]:
        total += single_series
    return total

def NSK129(userloads):
    """Returns userloads for transformatorkrets NSK129-T1."""
    nsk129 = NSK129_user_ids()
    total = userloads.read(nsk129[0])
    for user_id in nsk129[1:]:
        total += userloads.read(user_id)
    return total

def NSK129_user_ids():
    """Returns user ids for NSK129-T1, without Mann Jagjot Kaur."""
    return [
707057500045751944,
707057500045752170,
707057500045752255,
707057500045752231,
707057500045752217,
707057500045752194,
707057500045752156,
707057500045752132,
707057500045752118,
707057500045752088,
707057500045752064,
707057500045752057,
707057500045752033,
707057500045752002,
707057500045751982,
707057500045751975,
707057500045751937,
707057500045751913,
707057500045745844,
707057500045745851,
707057500045745929,
707057500045745936,
707057500045746001,
707057500045746018,
707057500045745868,
707057500045745875,
707057500045745943,
707057500045745950,
707057500045746025,
707057500045746032,
707057500045745882,
707057500045745837,
707057500045745899,
707057500045745974,
707057500045746049,
707057500045746056,
707057500045745905,
707057500045745981,
707057500045745998,
707057500045746063,
707057500045746070,
707057500045745912,
707057500045745639,
707057500045745707,
707057500045745714,
707057500045745783,
707057500045745790,
707057500045745646,
707057500045745653,
707057500045745738,
707057500045745806,
707057500045745615,
707057500045745776,
707057500045745622,
707057500045745578,
707057500045745585,
707057500045745592,
707057500045745813,
707057500045745660,
707057500045745684,
707057500045745721,
707057500045745769,
707057500045745677,
707057500045745745,
707057500045745752,
707057500045745608,
707057500045750442,
707057500045752613,
707057500045752606,
707057500045752163,
707057500045752200,
707057500045752224,
707057500045752149,
707057500045752187,
707057500045752293,
707057500045752286,
707057500045752071,
707057500045752040,
707057500045752095,
707057500045752125,
707057500045752101,
707057500045752026,
707057500045752279,
707057500045752262,
707057500045751814,
707057500045751807,
707057500045751890,
707057500045751883,
707057500045751876,
707057500045751869,
707057500045751821,
707057500045751838,
707057500045751845,
707057500045751852,
707057500045751999,
707057500045751951,
707057500045752019,
707057500045751920,
707057500045751968,
707057500045751906,
707057500045745691,
707057500045745967]

def total_load_in_experiment_periods(userloads, user_ids):
    """Return a list of time series containing the total load for the given
    users in the experiment periods."""
    periods = experiment_periods()
    return [total_load(userloads, user_ids, period) for period in periods]

def mean_experiment_load_for_user_subset(num_users, seed=None):
    """Return a list of time series containing the total load over the
    experiment periods for the user_ids selected to be part of the
    clean+predict experiment."""
    loads = tempfeeder_exp()
    if seed is None:
        seed = np.random.randint(1, 2**16)
    user_ids = np.random.RandomState(seed).permutation(loads.user_ids)[:num_users]
    return [l / len(user_ids) for l in total_load_in_experiment_periods(loads, user_ids)]

def total_experiment_load():
    """Return a list of time series containing the total load over the
    experiment periods for the user_ids selected to be part of the
    clean+predict experiment."""
    loads = tempfeeder_exp()
    return total_load_in_experiment_periods(loads, loads.user_ids)

if __name__ == "__main__":
    from unittest import main
    main(module="test_" + __file__[:-3])
