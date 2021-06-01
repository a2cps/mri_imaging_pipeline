import pandas as pd
import numpy as np

def main():
    participants_df = pd.read_csv('participants.tsv', sep='\t')
    participants_df = participants_df.replace(np.nan, 'n/a')
    participants_df.to_csv('participants.tsv', sep="\t", index = False)
    return

if __name__ == '__main__':
    main()