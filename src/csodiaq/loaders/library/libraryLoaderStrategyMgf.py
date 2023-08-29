from csodiaq.loaders.library.libraryLoaderStrategy import (
    LibraryLoaderStrategy,
    create_peaks_from_mz_intensity_lists_and_csodiaq_key_id,
    remove_low_intensity_peaks_below_max_peak_num,
    finalVariableNames,
)
import os
from pyteomics import mgf
import re


class LibraryLoaderStrategyMgf(LibraryLoaderStrategy):
    """
    Concrete strategy implementation of the LibraryLoaderStrategy strategy class specific for
        loading mgf library files into a standardized dictionary for use in CsoDIAq.

    Attributes
    ----------
    rawUploadedLibraryObject : pyteomics.mgf.IndexedMGF
        The original mgf library as loaded using the pyteomics mgf class.
    """

    def _load_raw_library_object_from_file(self, libraryFilePath: os.PathLike) -> None:
        self.rawUploadedLibraryObject = mgf.read(libraryFilePath)

    def _format_raw_library_object_into_csodiaq_library_dict(self) -> dict:
        maxPeakNum = 10
        csodiaqLibDict = {}
        rawIdxSortedByCsodiaqKey = []
        for csodiaqKeyIdx in range(len(self.rawUploadedLibraryObject)):
            librarySpectrum = self.rawUploadedLibraryObject[csodiaqKeyIdx]
            csodiaqKey, csodiaqValue = _create_csodiaq_library_entry(
                librarySpectrum, maxPeakNum, csodiaqKeyIdx
            )
            csodiaqLibDict[csodiaqKey] = csodiaqValue
        csodiaqLibDict = _rewrite_csodiaq_key_idx_to_correspond_to_sorted_csodiaq_key(csodiaqLibDict)
        return csodiaqLibDict


def _rewrite_csodiaq_key_idx_to_correspond_to_sorted_csodiaq_key(csodiaqLibDict):
    sortedLibKeys = sorted(csodiaqLibDict.keys())
    for i, key in enumerate(sortedLibKeys):
        oldPeaks = csodiaqLibDict[key][finalVariableNames["peaks"]]
        newPeaks = [(peak[0],peak[1],i) for peak in oldPeaks]
        csodiaqLibDict[key][finalVariableNames["peaks"]] = newPeaks
    return csodiaqLibDict

def _create_csodiaq_library_entry(
    librarySpectrum: dict, maxPeakNum: int, csodiaqKeyIdx: int
) -> dict:
    (
        csodiaqKey,
        precursorCharge,
        identifier,
        proteinName,
        isDecoy,
    ) = _extract_variables_from_spectrum_metadata(librarySpectrum["params"])
    peaks = create_peaks_from_mz_intensity_lists_and_csodiaq_key_id(
        librarySpectrum["m/z array"], librarySpectrum["intensity array"], csodiaqKeyIdx
    )
    reducedPeaks = remove_low_intensity_peaks_below_max_peak_num(peaks, maxPeakNum)
    return csodiaqKey, {
        finalVariableNames["precursorCharge"]: precursorCharge,
        finalVariableNames["identification"]: identifier,
        finalVariableNames["proteinName"]: proteinName,
        finalVariableNames["peaks"]: sorted(reducedPeaks),
        finalVariableNames["csodiaqKeyIdx"]: csodiaqKeyIdx,
        finalVariableNames["isDecoy"]: isDecoy,
    }


def _extract_variables_from_spectrum_metadata(metadata):
    csodiaqKey = (metadata["pepmass"][0], metadata["seq"])
    charge = int(re.sub("[+-]", "", str(metadata["charge"][0])))
    name = metadata["title"]
    if "protein" in metadata:
        protein = metadata["protein"]
    else:
        protein = ""
    if "DECOY" in name:
        decoy = 1
    else:
        decoy = 0
    return csodiaqKey, charge, name, protein, decoy
