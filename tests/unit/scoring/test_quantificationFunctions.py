import pytest
import pandas as pd
import numpy as np

from csodiaq.scoring.quantificationFunctions import (
    calculate_ion_count_from_peptides_of_protein,
    calculate_ion_count_for_each_protein_in_protein_fdr_df,
    compile_ion_count_comparison_across_runs_df,
    compile_common_protein_quantification_file,
    maxlfq,
)


@pytest.fixture
def ionCountList():
    return [
        100.0,
        200.0,
        300.0,
    ]


def test__quantification_functions__calculate_ion_count_from_peptides_of_protein(
    ionCountList,
):
    expectedOutput = 200.0
    output = calculate_ion_count_from_peptides_of_protein(ionCountList)
    assert expectedOutput == output


def test__quantification_functions__calculate_ion_count_for_each_protein_in_protein_fdr_df():
    inputData = [
        ["1/protein1", 100.0],
        ["1/protein1", 200.0],
        ["1/protein1", 300.0],
        ["2/protein2/protein3", 400.0],
        ["2/protein2/protein3", 500.0],
    ]

    inputDf = pd.DataFrame(inputData, columns=["leadingProtein", "ionCount"])
    expectedOutputData = [
        ["protein1", 200.0],
        ["protein2", 450.0],
        ["protein3", 450.0],
    ]
    expectedOutputDf = pd.DataFrame(expectedOutputData, columns=["protein", "ionCount"])
    outputDf = calculate_ion_count_for_each_protein_in_protein_fdr_df(inputDf)
    assert expectedOutputDf.equals(outputDf)


def test__quantification_functions__compile_ion_count_comparison_across_runs_df():
    columnName = "value"
    inputDf1 = pd.DataFrame(
        [
            ["p1", 100.0],
            ["p2", 200.0],
            ["p3", 300.0],
        ],
        columns=[columnName, "ionCount"],
    )
    inputDf2 = pd.DataFrame(
        [
            ["p3", 400.0],
            ["p4", 500.0],
            ["p5", 600.0],
        ],
        columns=[columnName, "ionCount"],
    )
    inputDf3 = pd.DataFrame(
        [
            ["p2", 700.0],
            ["p3", 800.0],
            ["p4", 900.0],
            ["p6", 1000.0],
        ],
        columns=[columnName, "ionCount"],
    )
    inputDfs = {
        "df1": inputDf1,
        "df2": inputDf2,
        "df3": inputDf3,
    }
    expectedOutputDf = pd.DataFrame(
        [
            [100.0, 200.0, 300.0, 0, 0, 0],
            [0, 0, 400.0, 500.0, 600.0, 0],
            [0, 700.0, 800.0, 900.0, 0, 1000.0],
        ],
        columns=[f"p{i}" for i in range(1, 7)],
        index=["df1", "df2", "df3"],
    )
    outputDf = compile_ion_count_comparison_across_runs_df(inputDfs, columnName)
    assert expectedOutputDf.equals(outputDf)

def test__quantification_functions__compile_common_protein_quantification_file__averaging_method():
    inputData = [
        ["1/protein1", 100.0],
        ["1/protein1", 200.0],
        ["1/protein1", 300.0],
        ["2/protein2/protein3", 400.0],
        ["2/protein2/protein3", 500.0],
    ]
    inputDf1 = pd.DataFrame(inputData, columns=["leadingProtein", "ionCount"])
    inputDf2 = inputDf1.copy()
    fileHeader1 = 'test1'
    fileHeader2 = 'test2'
    expectedOutputDf = pd.DataFrame(
        [[200.0, 450.0, 450.0],
         [200.0, 450.0, 450.0]],
        columns=['protein1','protein2','protein3'],
        index=[fileHeader1, fileHeader2]
    )
    outputDf = compile_common_protein_quantification_file({
        fileHeader1:inputDf1,
        fileHeader2: inputDf2,
    }, commonPeptidesDf=None, proteinQuantificationMethod='average')
    assert expectedOutputDf.equals(outputDf)

def test__maxlfq__from_paper():
    """
    Tests the maxLFQ algorithm for protein quantification as summarized in in figure 2 of their paper.

    The test is based on figure 2. The following table is in plot C:
      P1 P2 P3 P4 P5 P6 P7
    A  -  X  -  -  -  X  -
    B  -  X  X  -  -  X  -
    C  X  X  X  X  -  X  X
    D  X  X  -  X  -  X  X
    E  -  X  -  X  -  -  X
    F  -  X  -  -  X  -  -

    I created a dataframe where each sample (letter) has a specific proportion (1-6) applied to it's peptides.
        Peptides have an initial size that is multiplied by this proportion (0.001 to 1000, 7 orders of magnitude).

        P1    P2   P3   P4    P5     P6      P7
    A  0.006  0.06  0.6  6.0  60.0  600.0  6000.0
    B  0.005  0.05  0.5  5.0  50.0  500.0  5000.0
    C  0.004  0.04  0.4  4.0  40.0  400.0  4000.0
    D  0.003  0.03  0.3  3.0  30.0  300.0  3000.0
    E  0.002  0.02  0.2  2.0  20.0  200.0  2000.0
    F  0.001  0.01  0.1  1.0  10.0  100.0  1000.0

    Applying the selection in the first table, you'd end up with the following input dataframe.

        P1    P2   P3   P4    P5     P6      P7
    A  0      0.06  0    0     0    600.0       0
    B  0      0.05  0.5  0     0    500.0       0
    C  0.004  0.04  0.4  4.0   0    400.0  4000.0
    D  0.003  0.03  0    3.0   0    300.0  3000.0
    E  0      0.02  0    2.0   0        0  2000.0
    F  0      0.01  0    0    10.0      0       0

    In this example, you would expect exactly the following ratios to exist:

       A    B    C    D    E    F
    A  -    -    -    -    -    -
    B  6:5  -    -    -    -    -
    C  6:4  5:4  -    -    -    -
    D  6:3  5:3  4:3  -    -    -
    E  6:2  5:2  4:2  3:2  -    -
    F  6:1  5:1  4:1  3:1  2:1  -

    Applying the maxLFQ function to this input, you'd expect quantities that reflect these ratios.




    """
    numPeptides = 7
    numSamples = 6
    peptideIntensityIncrease = [10**i for i in range(-3,4)]
    sampleIntensityIncrease = list(range(numSamples, 0, -1))
    inputDf = pd.DataFrame(
        np.multiply.outer(sampleIntensityIncrease, peptideIntensityIncrease),
        columns=[f'P{i}' for i in range(1, numPeptides+1)],
        index=['A','B','C','D','E','F']
    )
    cellsToDelete = [
        (0, 0),
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 6),
        (1, 0),
        (1, 3),
        (1, 4),
        (1, 6),
        (2, 4),
        (3, 2),
        (3, 4),
        (4, 0),
        (4, 2),
        (4, 4),
        (4, 5),
        (5, 0),
        (5, 2),
        (5, 3),
        (5, 5),
        (5, 6),
    ]
    for cell in cellsToDelete:
        inputDf.iloc[cell[0],cell[1]] = 0

    normalizedInputDf = np.log(inputDf)
    expectedOutput = np.array([7.83589964, 7.65357809, 7.43065038, 7.14296831, 6.73758953, 0])

    output = maxlfq(normalizedInputDf.to_numpy())
    np.testing.assert_array_almost_equal(expectedOutput, output)







