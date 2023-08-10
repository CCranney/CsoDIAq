import os
import pandas as pd
from csodiaq import set_command_line_settings
from csodiaq.identification import Identifier
from csodiaq.utils import create_outfile_header
from csodiaq.scoring import create_spectral_fdr_output_from_full_output, create_peptide_fdr_output_from_full_output, create_protein_fdr_output_from_peptide_fdr_output
from csodiaq.targetedReanalysis import create_mass_spec_input_dataframes_for_targeted_reanalysis_of_identified_peptides

def main():
    parser = set_command_line_settings()
    args = vars(parser.parse_args())
    if args['command'] == 'gui' or args['command'] is None: pass
    elif args['command'] == 'id':
        run_identification(args)
    elif args["command"] == 'score':
        run_scoring(args)
    elif args["command"] == 'targetedReanalysis':
        run_targeted_reanalysis(args)

def run_identification(args):
    identifier = Identifier(args)
    for queryFile in args["input"]:
        identificationFullOutputDf = identifier.identify_library_spectra_in_query_file(queryFile)
        outFileHeader = create_outfile_header(args['output'], queryFile, args['correctionDegree'])
        identificationFullOutputDf.to_csv(f'{outFileHeader}_fullOutput.csv', index=False)

def run_scoring(args):
    outputDir = os.path.join(args["input"]["csodiaqDirectory"], f'fdrScores-{args["score"]}')
    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    for idDfFile in args["input"]["idFiles"]:
        fileHeader = extract_file_name_without_file_type(idDfFile)
        idDf = pd.read_csv(os.path.join(args["input"]["csodiaqDirectory"],idDfFile))
        spectralDf = create_spectral_fdr_output_from_full_output(idDf)
        spectralDf.to_csv(os.path.join(outputDir, f'{fileHeader}_spectralFDR.csv'), index=False)
        peptideDf = create_peptide_fdr_output_from_full_output(idDf)
        peptideDf.to_csv(os.path.join(outputDir, f'{fileHeader}_peptideFDR.csv'), index=False)
        proteinDf = create_protein_fdr_output_from_peptide_fdr_output(peptideDf) #TODO: This should be conditional on the presence of an appropriately-formatted protein column
        proteinDf.to_csv(os.path.join(outputDir, f'{fileHeader}_proteinFDR.csv'), index=False)

def run_targeted_reanalysis(args):
    outputDir = make_targeted_reanalysis_output_directory_name(args)
    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    if args["protein"]:
        scoreType = "protein"
    else:
        scoreType = "peptide"
    for scoreFdrFile in args["input"][scoreType]:
        fileHeader = extract_file_name_without_file_type(scoreFdrFile)
        scoreDf = pd.read_csv(os.path.join(args["input"]["csodiaqDirectory"],scoreFdrFile))
        targetedOutputDict = create_mass_spec_input_dataframes_for_targeted_reanalysis_of_identified_peptides(
            scoreDf,
            isIncludeHeavyIsotopes=args["heavyIsotope"],
            maximumPeptidesPerProtein=args["protein"],
        )
        for name, df in targetedOutputDict.items():
            if name == "fullDf":
                df.to_csv(os.path.join(outputDir, f'{name}_{fileHeader}.csv'), index=False)
            else:
                df.to_csv(os.path.join(outputDir, f'{name}_{fileHeader}.txt'), sep='\t', index=False)




def make_targeted_reanalysis_output_directory_name(args):
    if args['protein']:
        proteinHeader = f"maxPeptidesPerProtein{args['protein']}"
    else:
        proteinHeader = 'peptidesNoProteins'
    if args['heavyIsotope']:
        heavyHeader = 'includesHeavyIsotopes'
    else:
        heavyHeader = 'noHeavyIsotopes'
    newDirectoryName = f'targetedReanalysis_{proteinHeader}_{heavyHeader}'
    return os.path.join(args["input"]["csodiaqDirectory"], newDirectoryName)

def extract_file_name_without_file_type(file):
    return '.'.join(file.split('.')[:-1])

if __name__ == "__main__":
    main()
