from csodiaq.loaders.LibraryLoaderStrategy import LibraryLoaderStrategy, create_peaks_from_mz_intensity_lists_and_csodiaq_key_id, remove_low_intensity_peaks_below_max_peak_num, finalVariableNames
import pandas as pd
import os

class LibraryLoaderStrategyTable(LibraryLoaderStrategy):

    def _load_raw_library_object_from_file(self, libraryFilePath: os.PathLike) -> None:
        if libraryFilePath.endswith('.tsv'): separator='\t'
        else: separator=','
        self.rawLibDf = pd.read_csv(libraryFilePath, sep=separator)
        self.oldToNewColumnDict = _set_old_to_new_column_dict(libraryFilePath)
        _assert_there_are_no_missing_columns(self.oldToNewColumnDict.keys(), self.rawLibDf.columns)

    def _format_raw_library_object_into_csodiaq_library_dict(self) -> dict:
        maxPeakNum = 10
        reformattedLibDf = _reformat_raw_library_object_columns(self.rawLibDf, self.oldToNewColumnDict)
        organizedDataDict = _organize_data_by_csodiaq_library_dict_keys(reformattedLibDf)
        csodiaqLibraryDict = {}
        for csodiaqKeyIdx in range(len(organizedDataDict['csodiaqKeys'])):
            csodiaqKey, csodiaqValue = _create_csodiaq_library_entry(organizedDataDict, maxPeakNum, csodiaqKeyIdx)
            csodiaqLibraryDict[csodiaqKey] = csodiaqValue
        return csodiaqLibraryDict

def _assert_there_are_no_missing_columns(requiredColumns: list, presentColumns: list) -> None:
    missingColumnValues = set(requiredColumns) - set(presentColumns)
    if len(missingColumnValues):
        raise ValueError(
            f'table library file is missing expected column(s). Missing values: [{", ".join(sorted(missingColumnValues))}])'
        )

def _reformat_raw_library_object_columns(df: pd.DataFrame, oldToNewColumnDict: dict) -> pd.DataFrame:
    reformattedDf = df[oldToNewColumnDict.keys()]
    reformattedDf = reformattedDf.rename(columns=oldToNewColumnDict)
    reformattedDf['csodiaqLibKey'] = list(zip(reformattedDf['precursorMz'].tolist(),
                          reformattedDf['peptideName'].tolist()))
    return reformattedDf

def _organize_data_by_csodiaq_library_dict_keys(df: pd.DataFrame) -> dict:
    keys = sorted(set(df['csodiaqLibKey']))
    mz = df.groupby('csodiaqLibKey')['peakMz'].apply(list).to_dict()
    intensities = df.groupby('csodiaqLibKey')['peakIntensity'].apply(list).to_dict()
    df.drop_duplicates(subset='csodiaqLibKey', inplace=True)
    df.set_index('csodiaqLibKey', drop=True, inplace=True)
    df.drop(['precursorMz','peakMz','peptideName','peakIntensity'], axis=1, inplace=True)
    metadata = df.to_dict(orient='index')
    return {
        'csodiaqKeys': keys,
        'mz':mz,
        'intensities':intensities,
        'metadata':metadata
    }

def _create_csodiaq_library_entry(organizedDataDict: dict, maxPeakNum: int, csodiaqKeyIdx: int) -> dict:
    csodiaqKey = organizedDataDict['csodiaqKeys'][csodiaqKeyIdx]
    peaks = create_peaks_from_mz_intensity_lists_and_csodiaq_key_id(organizedDataDict['mz'][csodiaqKey],
                                                                    organizedDataDict['intensities'][csodiaqKey],
                                                                    csodiaqKeyIdx)
    reducedPeaks = remove_low_intensity_peaks_below_max_peak_num(peaks, maxPeakNum)
    isDecoy = int('decoy' in organizedDataDict['metadata'][csodiaqKey]['proteinName'].lower())
    # NOTE: some of these names are not intuitive (commented versions better). Switch when working on future dependencies.
    return csodiaqKey, {
                finalVariableNames['precursorCharge']: organizedDataDict['metadata'][csodiaqKey]['precursorCharge'],
                finalVariableNames['identifier']: organizedDataDict['metadata'][csodiaqKey]['identifier'],
                finalVariableNames['proteinName']: organizedDataDict['metadata'][csodiaqKey]['proteinName'],
                finalVariableNames['peaks']: sorted(reducedPeaks),
                finalVariableNames['csodiaqKeyIdx']: csodiaqKeyIdx,
                finalVariableNames['isDecoy']: isDecoy,
    }

def _set_old_to_new_column_dict(filePath):
    librarySource = _determine_library_source_from_file(filePath)
    newColumns = [
        'precursorMz',
        'peptideName',
        'peakMz',
        'peakIntensity',
        'precursorCharge',
        'identifier',
        'proteinName',
    ]
    if librarySource == 'spectrast':
        oldColumns = [
            'PrecursorMz',
            'FullUniModPeptideName',
            'ProductMz',
            'LibraryIntensity',
            'PrecursorCharge',
            'transition_group_id',
            'ProteinName',
        ]
        return dict(zip(oldColumns, newColumns))
    elif librarySource == 'fragpipe':
        oldColumns = [
            'PrecursorMz',
            'ModifiedPeptideSequence',
            'ProductMz',
            'LibraryIntensity',
            'PrecursorCharge',
            'PeptideSequence',
            'ProteinId',
        ]
        return dict(zip(oldColumns, newColumns))
    elif librarySource == 'prosit':
        oldColumns = [
            'PrecursorMz',
            'ModifiedPeptide',
            'FragmentMz',
            'RelativeIntensity',
            'PrecursorCharge',
            'StrippedPeptide',
            'FragmentLossType',
        ]
        return dict(zip(oldColumns, newColumns))

def _determine_library_source_from_file(filePath):
    with open(filePath) as f:
        columns = f.readline()
        if 'transition_group_id' in columns: return 'spectrast'
        elif 'ProteinId' in columns: return 'fragpipe'
        elif 'RelativeIntensity' in columns: return 'prosit'
        else: raise ValueError('The library table file provided does not match spectrast, fragpipe, or prosit formats.')
