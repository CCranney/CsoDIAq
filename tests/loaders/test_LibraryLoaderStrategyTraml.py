import pytest
import os
import pandas as pd
import re
from tempfile import TemporaryDirectory, NamedTemporaryFile
from csodiaq.loaders.LibraryLoaderStrategyTraml import LibraryLoaderStrategyTraml, reformat_raw_library_object_columns, organize_data_by_csodiaq_library_dict_keys

@pytest.fixture
def loader():
    return LibraryLoaderStrategyTraml('spectrast')

def test__library_loader_strategy_traml__initialization(loader): pass

@pytest.fixture
def libFilePath():
    cwd = os.getcwd()
    parent = os.path.dirname(cwd)
    return os.path.join(parent,  'test_files', 'sample_lib_traml_spectrast.tsv')

def test__library_loader_strategy_traml__load_raw_library_object_from_file__spectrast_library(loader, libFilePath):
    loader._load_raw_library_object_from_file(libFilePath)
    assert hasattr(loader, 'rawLibDf')
    assert isinstance(loader.rawLibDf, pd.DataFrame)

def check_value_error_thrown_when_missing_columns(loader, dfPath, missingColumnValues):
    if dfPath.endswith('.tsv'):
        separator = '\t'
    else:
        separator = ','
    libDf = pd.read_csv(dfPath, sep=separator)
    libDf.drop(missingColumnValues, axis=1, inplace=True)
    invalidLibFile = NamedTemporaryFile(prefix=f'csodiaq_traml_loader_missing_column_{"_".join(missingColumnValues)}_', suffix=".tsv")
    libDf.to_csv(invalidLibFile.name, sep='\t', index=False)
    errorOutput = f'traml spectrast library file is missing expected column(s). Missing values: [{", ".join(sorted(missingColumnValues))}])'
    with pytest.raises(ValueError, match=re.escape(errorOutput)):
        loader._load_raw_library_object_from_file(invalidLibFile.name)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__PrecursorMz(loader, libFilePath):
    missingColumnValues = ['PrecursorMz']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__FullUniModPeptideName(loader, libFilePath):
    missingColumnValues = ['FullUniModPeptideName']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__PrecursorCharge(loader, libFilePath):
    missingColumnValues = ['PrecursorCharge']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__ProductMz(loader, libFilePath):
    missingColumnValues = ['ProductMz']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__LibraryIntensity(loader, libFilePath):
    missingColumnValues = ['LibraryIntensity']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__transition_group_id(loader, libFilePath):
    missingColumnValues = ['transition_group_id']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__ProteinName(loader, libFilePath):
    missingColumnValues = ['ProteinName']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__spectrast_library__2_columns_missing(loader, libFilePath):
    missingColumnValues = ['ProteinName', 'LibraryIntensity']
    check_value_error_thrown_when_missing_columns(loader, libFilePath, missingColumnValues)

def test__library_loader_strategy_traml__format_raw_library_object_into_csodiaq_library_dict__spectrast_library(loader, libFilePath):
    loader._load_raw_library_object_from_file(libFilePath)
    outputDict = loader._format_raw_library_object_into_csodiaq_library_dict()
    expectedOutputDict = {
        (375.87322429333335, 'FANYIDKVR'): {
            'PrecursorCharge': 3,
            'transition_group_id': '1_FANYIDKVR_3',
            'ProteinName': '1/sp|P08670|VIME_HUMAN',
            'Peaks': [(333.15573166, 1072.6, 0), (397.23197061, 2082.7, 0), (402.2823291699999, 4930.4, 0), (445.738434336, 746.7, 0), (454.253434336, 1301.3, 0), (489.771991231, 1398.4, 0), (500.2792722, 863.7, 0), (517.3092722, 10000.0, 0), (630.393336182, 8235.6, 0), (793.4566647199999, 5098.5, 0)],
            'ID': 0,
            'Decoy': 0
        }
    }
    assert outputDict == expectedOutputDict

def test__library_loader_strategy_traml__reformat_raw_library_object_columns():
    numColumns = 10
    csodiaqKeyColumns = ['precursorMz', 'peptideName']
    oldMappedColumns = [str(i) for i in range(numColumns)]
    newMappedColumns = [columnName + '_new' for columnName in oldMappedColumns]
    oldMappedColumns += csodiaqKeyColumns
    newMappedColumns += csodiaqKeyColumns
    oldToNewColumnDict = dict(zip(oldMappedColumns, newMappedColumns))
    superfluousColumns = ['random', 'superfluous', 'columns']
    oldColumns = oldMappedColumns + superfluousColumns
    newColumns = newMappedColumns + ['csodiaqLibKey']
    data = [
        [0 for i in range(len(oldColumns))]
    ]
    df = pd.DataFrame(data, columns = oldColumns)
    newDf = reformat_raw_library_object_columns(df, oldToNewColumnDict)
    assert set(newDf.columns) == set(newColumns)

def test__library_loader_strategy_traml__organize_data_by_csodiaq_library_dict_keys(loader, libFilePath):
    loader._load_raw_library_object_from_file(libFilePath)
    reformattedDf = reformat_raw_library_object_columns(loader.rawLibDf, loader.oldToNewColumnDict)
    expectedKeys = [(375.87322429333335, 'FANYIDKVR')]
    expectedTupleToListMzDict = {(375.87322429333335, 'FANYIDKVR'): [517.3092722, 630.393336182, 793.4566647199999, 402.2823291699999, 397.23197061, 489.771991231, 454.253434336, 333.15573166, 500.2792722, 445.738434336]}
    expectedTupleToListIntensityDict = {(375.87322429333335, 'FANYIDKVR'): [10000.0, 8235.6, 5098.5, 4930.4, 2082.7, 1398.4, 1301.3, 1072.6, 863.7, 746.7]}
    expectedTupleToDictMetadataDict = {(375.87322429333335, 'FANYIDKVR'): {'identifier': '1_FANYIDKVR_3', 'proteinName': '1/sp|P08670|VIME_HUMAN', 'precursorCharge': 3}}
    dataDict = organize_data_by_csodiaq_library_dict_keys(reformattedDf)
    assert dataDict['csodiaqKeys'] == expectedKeys
    assert dataDict['mz'] == expectedTupleToListMzDict
    assert dataDict['intensities'] == expectedTupleToListIntensityDict
    assert dataDict['metadata'] == expectedTupleToDictMetadataDict

@pytest.fixture
def fragpipeLoader():
    return LibraryLoaderStrategyTraml('fragpipe')

@pytest.fixture
def fragpipeLibFilePath():
    cwd = os.getcwd()
    parent = os.path.dirname(cwd)
    return os.path.join(parent,  'test_files', 'sample_lib_traml_fragpipe.tsv')


def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__fragpipe_library__PrecursorMz(
        fragpipeLoader, fragpipeLibFilePath):
    missingColumnValues = ['PrecursorMz']
    check_value_error_thrown_when_missing_columns(fragpipeLoader, fragpipeLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__fragpipe_library__ModifiedPeptideSequence(
        fragpipeLoader, fragpipeLibFilePath):
    missingColumnValues = ['ModifiedPeptideSequence']
    check_value_error_thrown_when_missing_columns(fragpipeLoader, fragpipeLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__fragpipe_library__PrecursorCharge(
        fragpipeLoader, fragpipeLibFilePath):
    missingColumnValues = ['PrecursorCharge']
    check_value_error_thrown_when_missing_columns(fragpipeLoader, fragpipeLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__fragpipe_library__ProductMz(
        fragpipeLoader, fragpipeLibFilePath):
    missingColumnValues = ['ProductMz']
    check_value_error_thrown_when_missing_columns(fragpipeLoader, fragpipeLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__fragpipe_library__LibraryIntensity(
        fragpipeLoader, fragpipeLibFilePath):
    missingColumnValues = ['LibraryIntensity']
    check_value_error_thrown_when_missing_columns(fragpipeLoader, fragpipeLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__fragpipe_library__PeptideSequence(
        fragpipeLoader, fragpipeLibFilePath):
    missingColumnValues = ['PeptideSequence']
    check_value_error_thrown_when_missing_columns(fragpipeLoader, fragpipeLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__fragpipe_library__ProteinId(
        fragpipeLoader, fragpipeLibFilePath):
    missingColumnValues = ['ProteinId']
    check_value_error_thrown_when_missing_columns(fragpipeLoader, fragpipeLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__format_raw_library_object_into_csodiaq_library_dict__fragpipe_library(fragpipeLoader, fragpipeLibFilePath):
    fragpipeLoader._load_raw_library_object_from_file(fragpipeLibFilePath)
    outputDict = fragpipeLoader._format_raw_library_object_into_csodiaq_library_dict()
    expectedOutputDict = {
        (375.873226, 'FANYIDKVR'): {
            'PrecursorCharge': 3,
            'transition_group_id': 'FANYIDKVR',
            'ProteinName': 'P08670',
            'Peaks': [(175.118953, 2926.18, 0), (274.187367, 1647.689, 0), (333.155733, 1071.177, 0), (397.231972, 2078.822, 0), (402.282331, 4932.288, 0), (454.253437, 1301.4617, 0), (489.771994, 1395.553, 0), (517.309275, 10000.0, 0), (630.393339, 8233.006, 0), (793.456668, 5096.472, 0)],
            'ID': 0,
            'Decoy': 0
        }
    }
    assert outputDict == expectedOutputDict

@pytest.fixture
def prositLoader():
    return LibraryLoaderStrategyTraml('prosit')

@pytest.fixture
def prositLibFilePath():
    cwd = os.getcwd()
    parent = os.path.dirname(cwd)
    return os.path.join(parent,  'test_files', 'sample_lib_spectronaut_prosit.csv')


def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__prosit_library__PrecursorMz(
        prositLoader, prositLibFilePath):
    missingColumnValues = ['PrecursorMz']
    check_value_error_thrown_when_missing_columns(prositLoader, prositLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__prosit_library__ModifiedPeptideSequence(
        prositLoader, prositLibFilePath):
    missingColumnValues = ['ModifiedPeptide']
    check_value_error_thrown_when_missing_columns(prositLoader, prositLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__prosit_library__PrecursorCharge(
        prositLoader, prositLibFilePath):
    missingColumnValues = ['PrecursorCharge']
    check_value_error_thrown_when_missing_columns(prositLoader, prositLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__prosit_library__ProductMz(
        prositLoader, prositLibFilePath):
    missingColumnValues = ['FragmentMz']
    check_value_error_thrown_when_missing_columns(prositLoader, prositLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__prosit_library__LibraryIntensity(
        prositLoader, prositLibFilePath):
    missingColumnValues = ['RelativeIntensity']
    check_value_error_thrown_when_missing_columns(prositLoader, prositLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__prosit_library__PeptideSequence(
        prositLoader, prositLibFilePath):
    missingColumnValues = ['ModifiedPeptide']
    check_value_error_thrown_when_missing_columns(prositLoader, prositLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__load_raw_library_object_from_file__fails_when_missing_required_columns__prosit_library__ProteinId(
        prositLoader, prositLibFilePath):
    missingColumnValues = ['FragmentLossType'] # NOTE: Make protein optional? This is just a placeholder
    check_value_error_thrown_when_missing_columns(prositLoader, prositLibFilePath, missingColumnValues)

def test__library_loader_strategy_traml__format_raw_library_object_into_csodiaq_library_dict__prosit_library(prositLoader, prositLibFilePath):
    prositLoader._load_raw_library_object_from_file(prositLibFilePath)
    outputDict = prositLoader._format_raw_library_object_into_csodiaq_library_dict()
    expectedOutputDict = {
        (374.1867597566666, '_MMPAAALIM[Oxidation (O)]R_'): {
            'PrecursorCharge': 3,
            'transition_group_id': 'MMPAAALIMR',
            'ProteinName': 'noloss',
            'Peaks': [(175.11895751953125, 1.0, 0), (263.0882568359375, 0.1923068910837173, 0), (322.15435791015625, 0.412596195936203, 0), (360.1410217285156, 0.085973247885704, 0), (431.1781311035156, 0.1523399353027343, 0), (435.2384033203125, 0.7306222915649414, 0), (502.2152404785156, 0.0825881585478782, 0), (548.322509765625, 0.3042449355125427, 0), (619.359619140625, 0.1164016127586364, 0), (690.396728515625, 0.0937163606286048, 0)],
            'ID': 0,
            'Decoy': 0
        }
    }
    assert outputDict == expectedOutputDict