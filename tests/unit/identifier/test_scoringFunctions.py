import pytest
import pandas as pd
import re
import numpy as np
from math import isclose

from csodiaq.identifier.scoringFunctions import (
    score_library_to_query_matches,
    calculate_cosine_similarity_score,
    calculate_macc_score,
    identify_all_decoys,
    determine_index_of_fdr_cutoff,
    calculate_fdr_rates_of_decoy_array,
    calculate_ppm_offset_tolerance,
    calculate_ppm_offset_tolerance_using_mean_and_standard_deviation,
    calculate_ppm_offset_tolerance_using_tallest_bin_peak,
    filter_matches_by_ppm_offset_and_tolerance,
    identify_index_of_max_distance_to_noise_from_tallest_bin,
)


@pytest.fixture
def vectorA():
    return pd.Series([1, 5, 10])


@pytest.fixture
def vectorB(vectorA):
    return vectorA + 1


def test__score_functions__calculate_cosine_similarity_score(vectorA, vectorB):
    AB = sum([vectorA[i] * vectorB[i] for i in range(len(vectorA))])
    A = sum([vectorA[i] ** 2 for i in range(len(vectorA))])
    B = sum([vectorB[i] ** 2 for i in range(len(vectorA))])
    expectedScore = AB / (A**0.5 * B**0.5)
    score = calculate_cosine_similarity_score(vectorA, vectorB)
    assert isclose(score, expectedScore)


def test__score_functions__calculate_macc_score(vectorA, vectorB):
    cosineSimilarity = calculate_cosine_similarity_score(vectorA, vectorB)
    expectedScore = (len(vectorA) ** (1 / 5)) * cosineSimilarity
    score = calculate_macc_score(vectorA, vectorB)
    assert score == expectedScore


def test__score_functions__score_library_to_query_matches(vectorA, vectorB):
    libraryIdx, queryIdx, ppmDiff = 1, 0, 0
    matchesDf = pd.DataFrame(
        index=vectorA.index,
        columns=[
            "libraryIdx",
            "libraryIntensity",
            "queryIdx",
            "queryIntensity",
        ],
    )
    matchesDf["libraryIdx"] = [libraryIdx for i in vectorA.index]
    matchesDf["libraryIntensity"] = vectorA
    matchesDf["queryIdx"] = [queryIdx for i in vectorA.index]
    matchesDf["queryIntensity"] = vectorB
    cosineScore = calculate_cosine_similarity_score(vectorA, vectorB)
    maccScore = calculate_macc_score(vectorA, vectorB)
    expectedOutputDf = pd.DataFrame(
        data=[[libraryIdx, queryIdx, cosineScore, maccScore]],
        columns=["libraryIdx", "queryIdx", "cosineScore", "maccScore"],
    )
    outputDf = score_library_to_query_matches(matchesDf)
    assert expectedOutputDf.equals(outputDf)

    lowScoreMatchesDf = matchesDf.copy()
    lowScoreMatchesDf["libraryIdx"] = [libraryIdx - 1 for i in vectorA.index]
    reverseVectorA = pd.Series(list(vectorA)[::-1])
    lowScoreMatchesDf["libraryIntensity"] = reverseVectorA
    lowCosineScore = calculate_cosine_similarity_score(reverseVectorA, vectorB)
    lowMaccScore = calculate_macc_score(reverseVectorA, vectorB)
    unsortedMatchesDf = pd.concat([lowScoreMatchesDf, matchesDf])
    expectedOutputDf = pd.DataFrame(
        data=[
            [libraryIdx, queryIdx, cosineScore, maccScore],
            [libraryIdx - 1, queryIdx, lowCosineScore, lowMaccScore],
        ],
        columns=["libraryIdx", "queryIdx", "cosineScore", "maccScore"],
    )
    sortedOutputDf = score_library_to_query_matches(unsortedMatchesDf)
    assert expectedOutputDf.equals(sortedOutputDf)


def test__score_functions__identify_all_decoys():
    isNotDecoy, isDecoy = 0, 1
    targetLibraryIdx, decoyLibraryIdx, queryIdx = 0, 1, 0

    scoreData = [
        [targetLibraryIdx, queryIdx],
        [decoyLibraryIdx, queryIdx],
    ]
    scoreDf = pd.DataFrame(scoreData, columns=["libraryIdx", "queryIdx"])
    expectedOutput = np.array([isNotDecoy, isDecoy])
    decoySet = set([decoyLibraryIdx])
    output = identify_all_decoys(decoySet, scoreDf)
    assert np.array_equal(output, expectedOutput)


def test__score_functions__calculate_fdr_rates_of_decoy_array():
    numberOfNonDecoys = 100
    decoys = [1, 1]
    isDecoySeries = np.array([0] * numberOfNonDecoys + decoys)
    expectedFdrs = [0] * numberOfNonDecoys
    expectedFdrs.append(1 / (numberOfNonDecoys + 1))
    expectedFdrs.append(2 / (numberOfNonDecoys + 2))
    fdrs = calculate_fdr_rates_of_decoy_array(isDecoySeries)
    np.testing.assert_array_equal(expectedFdrs, fdrs)


def test__score_functions__determine_index_of_fdr_cutoff():
    fdrCutoff = 0.01
    numberOfNonDecoys = int(1 / fdrCutoff)
    decoys = [1, 1]
    isDecoySeries = np.array([0] * numberOfNonDecoys + decoys)
    indexCutoff = determine_index_of_fdr_cutoff(isDecoySeries)
    lastDecoyIdx = numberOfNonDecoys + len(decoys) - 1
    assert indexCutoff == lastDecoyIdx


def test__score_functions__determine_index_of_fdr_cutoff__first_decoy_appears_before_fdr_cutoff():
    numberOfNonDecoys = 1
    decoys = [1]
    isDecoySeries = np.array([0] * numberOfNonDecoys + decoys)
    indexCutoff = determine_index_of_fdr_cutoff(isDecoySeries)
    lastDecoyIdx = numberOfNonDecoys + len(decoys) - 1
    assert indexCutoff == lastDecoyIdx


def test__score_functions__determine_index_of_fdr_cutoff__throws_error_when_top_score_is_decoy():
    numberOfNonDecoys = 0
    decoys = [1]
    isDecoySeries = np.array([0] * numberOfNonDecoys + decoys)
    errorOutput = "None of the library peptides were identified in the query spectra (highest score was a decoy)."
    with pytest.raises(ValueError, match=re.escape(errorOutput)):
        indexCutoff = determine_index_of_fdr_cutoff(isDecoySeries)


def test__score_functions__determine_index_of_fdr_cutoff__returns_original_df_when_no_decoys_found():
    numberOfNonDecoys = 10
    decoys = []
    isDecoySeries = np.array([0] * numberOfNonDecoys + decoys)
    indexCutoff = determine_index_of_fdr_cutoff(isDecoySeries)
    assert indexCutoff == numberOfNonDecoys


def test__score_functions__calculate_ppm_offset_tolerance_using_mean_and_standard_deviation():
    mean = 10
    stdDev1 = 2
    stdDev2 = 4
    numbers = [7, 8, 9, 10, 11, 12, 13]
    (
        offset,
        tolerance,
    ) = calculate_ppm_offset_tolerance_using_mean_and_standard_deviation(numbers, 1)
    assert offset == mean
    assert tolerance == stdDev1

    (
        offset,
        tolerance,
    ) = calculate_ppm_offset_tolerance_using_mean_and_standard_deviation(numbers, 2)
    assert offset == mean
    assert tolerance == stdDev2


def test__score_functions__calculate_ppm_offset_tolerance_using_tallest_bin_peak():
    numBins = 200
    tallestBin = 50
    tallestBinQuantity = 100
    mediumLeftNeighboringBin = tallestBin - 1
    mediumRightNeighboringBin = tallestBin + 1
    numbers = list(range(-numBins // 2, numBins // 2))
    numbers += [tallestBin] * (tallestBinQuantity - 1)
    numbers += [mediumLeftNeighboringBin] * (tallestBinQuantity // 2 - 1)
    numbers += [mediumRightNeighboringBin] * (tallestBinQuantity // 2 - 1)
    expectedOffset = tallestBin
    expectedTolerance = 2
    offset, tolerance = calculate_ppm_offset_tolerance_using_tallest_bin_peak(numbers)
    assert abs(offset - expectedOffset) < 0.5
    assert abs(tolerance - expectedTolerance) < 0.5

def test__score_functions__identify_index_of_max_distance_to_noise_from_tallest_bin():
    noisePeakHeight = 1
    mediumPeakHeight = 50
    tallestPeakHeight = 100
    numNoisePeaks = 11
    numMediumPeaksLeft = 3
    numMediumPeaksRight = 2
    peaks = \
        [noisePeakHeight] * numNoisePeaks + \
        [mediumPeakHeight] * numMediumPeaksLeft + \
        [tallestPeakHeight] + \
        [mediumPeakHeight] * numMediumPeaksRight + \
        [noisePeakHeight] * numNoisePeaks
    tallestPeakIdx = numNoisePeaks + numMediumPeaksLeft
    expectedIdx = numNoisePeaks - 1
    idx = identify_index_of_max_distance_to_noise_from_tallest_bin(np.array(peaks), tallestPeakIdx)
    assert expectedIdx == idx

def test__score_functions__filter_matches_by_ppm_offset_and_tolerance():
    libIdx = 0
    queryIdx = 0
    ppmOffset = 6
    matches = [[libIdx, queryIdx, (i * 5) + ppmOffset] for i in range(-5, 6)]
    columns = [
        "libraryIdx",
        "queryIdx",
        "ppmDifference",
    ]
    input = pd.DataFrame(matches, columns=columns)
    ppmTolerance = 11
    expectedOutput = input.iloc[3:-3,].reset_index(drop=True)
    output = filter_matches_by_ppm_offset_and_tolerance(input, ppmOffset, ppmTolerance)
    assert expectedOutput.equals(output)
