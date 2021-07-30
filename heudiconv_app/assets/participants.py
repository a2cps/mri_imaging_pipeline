import sys, os
import pandas as pd

def main(bids_root):
    participants_df = pd.read_csv(os.path.join(bids_root, 'participants.tsv'), sep='\t')
    participants_df = participants_df.fillna('n/a')
    participants_df.to_csv(os.path.join(bids_root, 'participants.tsv'), sep="\t", index = False)
    return

if __name__ == '__main__':
    try:
        bids_root = sys.argv[1]
        main(bids_root)
    except:
        raise ValueError("Please specify the path to the subject directory.")

