import json
import sys

def main():
    submitted_scans = json.loads(sys.argv[1])
    print(submitted_scans)

if __name__ == '__main__':
    main()



from output_check import *
scans_indicated = { 
                "subject_id": "10011",
                "visit": "V3",
                "T1 Indicated": "1",
                "DWI Indicated": "1",
                "fMRI Individualized Pressure Indicated": "1",
                "fMRI Standard Pressure Indicated": "1",
                "1st Resting State Indicated": "1",
                "2nd Resting State Indicated": "1"
                }
bids='/corral-secure/projects/A2CPS/products/mris/UI_uic/bids/UI10011V1'
report_csv = 'test.xls'
processed_scans = find_processed(bids)
scan_report = {**scans_indicated, **processed_scans}
df = pd.DataFrame(scan_report.items()).T
new_header = df.iloc[0] #grab the first row for the header
df = df[1:] #take the data less the header row
df.columns = new_header #set the header row as the df header
df.to_csv('test2.csv')

x=df
df1 = pd.DataFrame('background-color: ', index=x.index, columns=x.columns)
df1 = select_columns(x,df1,"T1 Received","T1 Indicated")
df1 = select_columns(x,df1,"DWI Received","DWI Indicated")
df1 = select_columns(x,df1,"fMRI Individualized Pressure Received","fMRI Individualized Pressure Indicated")
df1 = select_columns(x,df1,"fMRI Standard Pressure Received","fMRI Standard Pressure Indicated")
df1 = select_columns(x,df1,"1st Resting State Received","1st Resting State Indicated")
df1 = select_columns(x,df1,"2nd Resting State Received","2nd Resting State Indicated")


#df.style.apply(color_differences, axis=None)
df = df.style.apply(color_differences(df), axis=None)
df.to_excel(report_csv, engine="openpyxl", index = False)

writer = pd.ExcelWriter('pandas_conditional2.xlsx', engine='xlsxwriter')
# Get the xlsxwriter workbook and worksheet objects.
df.to_excel(writer, sheet_name='Sheet1')
workbook  = writer.book
worksheet = writer.sheets['Sheet1']

# Apply a conditional format to the cell range.
worksheet.conditional_format('B2:B8', {'type': '3_color_scale'})
writer.save()


cell_format = workbook.add_format()
cell_format.set_font_color('red')


def select_columns(x, df1,column1, column2):
    m1 = int(x[column1].iloc[0]) != int(x[column2].iloc[0])
    #print(x[column1].iloc[0], x[column2].iloc[0])
    #print(m1)
    if m1: 
        df1[column1] = np.where(m1, 'background-color: {}'.format('red'), df1[column1])
        df1[column2] = np.where(m1, 'background-color: {}'.format('red'), df1[column2])
    return df1