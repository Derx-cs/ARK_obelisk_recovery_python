import pandas as pd
from urllib.request import urlopen

csv_name_load="./Corrupted_Dinos_Recovery.csv" #if a csv file you want to load exists, enter the path
csv_name_write=csv_name_load #where your csv data should be written to, if you want to overwrite the database, keep it like this. If no name is given, writes to a standard name at script location
orig_player_data="./PlayerLocalData.arkprofile" #Path to the PlayerLocalData.arkprofile you want to fix (Typically in {Steam-folder}\steamapps\common\ARK\ShooterGame\Saved\LocalProfiles\) ALWAYS BACK THIS UP!
classical_flyer_repair_data="./Classical_Repair_PlayerLocalData.arkprofile" #where the data of the classical flyer repair should be written to #NOT CURRENTLY WORKING!
recovered_player_data="./Write_PlayerLocalData.arkprofile" #Where the uncorrupted Data should be written to (keep different from original file)

#some options
print_duplicate_message=False #print if a duplicate is found while generating data (checks for duplicates only in name, if the characters ever differ, we are lost)
print_added_dinos=True #if a print is done if a new dino is added to the data
print_unrecoverable_dinos=True #if a dino could not be recovered, print a message
print_recovered_dinos=True #if an output of all recovered dinos is given
encoding="latin_1"

def export_data_to_csv(data, filename):
    if(filename==""):
        filename="obelisk_recovery_data.csv"
        print("No csv name to export is given, use a standard one at script location")
    df=pd.DataFrame(data,columns=["name","hex_char_1","hex_char_2","path"])
    df.to_csv(filename,index=False)

def import_data_from_csv(filename):
    if(filename==""): #if no filename is iven, do not load csv
        print("No filename for csv to load is given, start with clean data")
        return []
    df=pd.read_csv(filename)
    data=df.values.tolist()
    return data

def import_database_from_web():
    data=[]
    #get the creature IDs ARK fandom page
    page=urlopen("https://ark.fandom.com/wiki/Creature_IDs")
    #read and decode it
    html_bytes = page.read()
    html = html_bytes.decode("utf-8")
    #find the begin of the table
    begin_table=html.find("<tbody><tr>")
    #repeat until you either run out of tables, or the character in front of the table is a ">" (marking the first non-data table on the site)
    while (begin_table!=-1 and html[begin_table-1]!=">"):
        #find the end of the table
        end_table=html.find("</tbody>")
        #only look at the table and split it in its rows (first 2 rows ignored, because of header)
        table=html[begin_table:end_table].split("<tr>")[2:]
        for tr in table:
            #split into the tabledata
            td=tr.split("</td>")
            #splice for the tags and get name in column 3
            name=td[3][5:-1]
            #split blueprintpath with the ' characters and add the _C and BlueprintgeneratedClass to match the Dinoclass saved
            Path="BlueprintGeneratedClass "+td[4].split("'")[1]+"_C" #TODO Make database not use the BlueprinGenerated Class , but need to adjust everywhere
            #the second chars number is actually just the size of the path+1
            second_char=len(Path)+1
            #the first chars number is actually just the second char plus a byte
            first_char=second_char+8
            #there are entries without a name, those do not interest us
            if(name!=""):
                data.append([name, first_char, second_char, Path])
                #print(name, first_char, second_char, Path)
        #after we did the table, cut it out of the html code and find the beginning of the new table
        html=html[end_table+1:]
        begin_table=html.find("<tbody><tr>")
    return data

def restore_classical_flyers(data, local_filename, target_filename):
    f=open(local_filename,"rb")
    g=open(target_filename,"wb")
    diff=0
    for line in f.readlines(): #look through the whole file
        class_name_loc=line.find(bytearray("DinoClassName",encoding))
        if(class_name_loc!=-1): #if we have a line which contains the Dinoclassname (we only ever need to edit these lines)
            if(line.find(bytearray("ClassicFlyers",encoding))!=-1):
                bluepr_name=line.find(bytearray("Blueprint",encoding))
                #now identify corrupt saves
                name_loc=line.find(bytearray('Character',encoding),bluepr_name) #find the last mention of "character" as this contains the species of dino, for which the other values are specific
                #find the lower end of the character name string, by finding the first control character in that direction
                for i in range(0,name_loc):
                    if(line[name_loc-i]==47):
                        mn=name_loc-i+1
                        break
                #find the upper end of the character name string, by finding the first control character in the other direction
                for j in range(name_loc,len(line)):
                    if(line[j]==46):
                        mx=j
                        break
                #save it as the name and cut the number on the tail end
                name_b=line[mn:mx]
                name=str(name_b,encoding)+"_C"
                #get the blueprint path name
                for dat in data:
                    if(dat[0]==name):
                        Path=dat[3]
                #cut the "Blueprintclass"
                path_start=Path.find(" ")+1
                #adjust for "Blueprint'[]'" and get lenght+1 as second char
                second_char=len(Path[path_start:-2])+12
                #add 4 to get the first char
                first_char=second_char+4
                diff+=first_char-line[bluepr_name-12]
                #print(diff)
                #print(second_char-line[bluepr_name-4])
                #build the newline relative from "Blueprint". Magic numbers splice exactly into the gaps for the chars
                newline=line[:bluepr_name-12]+bytearray(chr(first_char),encoding)+line[bluepr_name-11:bluepr_name-4]
                #insert second character
                newline=newline+bytearray(chr(second_char),encoding)+line[bluepr_name-3:bluepr_name+10]
                #insert Path
                newline=newline+bytearray(Path[path_start:-2],encoding)+line[-3:]
                g.write(newline)
            else:
                g.write(line)
        else:
            classic_pos=line.find(bytearray("Classic",encoding))
            if(classic_pos!=-1):
                a,b=line.split(bytearray("Classic",encoding))
                line=a+b
            g.write(line)

def extract_usable_dinos(filename,data=[]):#deprecated, just import the Database from the website
    f=open(filename,"rb")
    for line in f.readlines(): #look through the whole file
        #b=line       #convert to bytearray to make it mutable, 
        #print(b[3:12])
        if(line[3:12]==bytearray("DinoClass",encoding)): #if we have a line which contains the Dinoclass (we only ever need to edit these lines)
            #now identify corrupt saves
            if(line[32]!=8):
                name_loc=line.rfind(bytearray('Character',encoding),120,-1) #find the last mention of "character" as this contains the species of dino, for which the other values are specific
                #find the lower end of the character name string, by finding the first control character in that direction
                for i in range(0,name_loc):
                    if(line[name_loc-i]<10):
                        mn=name_loc-i+1
                        break
                #find the upper end of the character name string, by finding the first control character in the other direction
                for j in range(name_loc,len(line)):
                    if(line[j]<10):
                        mx=j
                        break
                #save it as the name and cut the number on the tail end
                name_b=line[mn:mx]
                name_b=name_b[:name_b.rfind(bytearray('C',encoding))+1]
                name=str(name_b,encoding)
                
                first_char=line[32]
                second_char=line[44]
                Path_b=line[48:line.find(bytes("\x00",encoding),50)]
                Path=str(Path_b,encoding)
                entry=[name,first_char,second_char,Path]
                dupe=False
                for dat in data:
                    if(dat[0]==name):
                        dupe=True
                        if(print_duplicate_message):
                            print("Found duplicate "+name+" while reading data!")
                if(dupe==False):
                    data.append(entry)
                    if(print_added_dinos):
                        print("Added "+name+ " to database!")
    return data

def fix_corrupted_dinos(data, import_filename ,export_filename):
    f=open(import_filename,"rb")
    g=open(export_filename,"wb")
    for line in f.readlines(): #look through the whole file
        b=line       #convert to bytearray to make it mutable, 
        if(line[3:12]==bytearray("DinoClass",encoding)): #if we have a line which contains the Dinoclass (we only ever need to edit these lines)
            #now identify corrupt saves
            if(line[32]==8):
                if(line.find(bytearray("Override",encoding))!=-1):
                    name_loc=line.find(bytearray('Override',encoding)) #Ice Wyvern are special, so we need to look for override
                else:
                    name_loc=line.rfind(bytearray('Character',encoding),120,-1) #find the last mention of "character" as this contains the species of dino, for which the other values are specific
                #find the lower end of the character name string, by finding the first control character in that direction
                for i in range(0,name_loc):
                    if(line[name_loc-i]<10):
                        mn=name_loc-i+1
                        break
                #find the upper end of the character name string, by finding the first control character in the other direction
                for j in range(name_loc,len(line)):
                    if(line[j]<10):
                        mx=j
                        break
                #save it as the name and cut the number on the tail end
                name_b=line[mn:mx]
                name_b=name_b[:name_b.rfind(bytearray('C',encoding))+1]
                name=str(name_b,encoding)
                found=False
                for dat in data:
                    if(dat[0]==name):
                        first_char=dat[1]
                        second_char=dat[2]
                        Path=dat[3]
                        found=True
                if(found==False):
                    if(print_unrecoverable_dinos):
                        print("Could not find "+name+ " in data, leaving corrupted dino data")
                    g.write(line)
                    continue
                else:
                    #found a corrupted dino to which we have a data entry
                    if(print_recovered_dinos):
                        print("Found a recoverable "+name+"! Recovering...")
                    #insert first character
                    b=b[:32]+bytearray(chr(first_char),encoding)+b[33:]
                    #insert the SOH
                    b=b[:40]+bytearray("\01",encoding)+b[40:]
                    #insert second character and nulls
                    b=b[:44]+bytearray(chr(second_char)+"\x00\x00",encoding)+b[44:]
                    #insert Path and null
                    b=b[:48]+bytearray(Path+"\00",encoding)+b[52:]
                    g.write(b)
            else:
                #we have found an uncorrupted entry, just leave it
                g.write(line)
        else:#if we dont have a Dinoclass line, just write it to the export
            g.write(line)

data=import_database_from_web() #importing the dino data from arkwiki (last supported release: Lost Island)
#restore_classical_flyers(data, orig_player_data, classical_flyer_repair_data) #restore the classical flyers (currently not working)
#data=import_data_from_csv(csv_name_load) #import data from csv
#data=extract_usable_dinos(orig_player_data,data) #add usable dino data to csv
#fix_corrupted_dinos(data,classical_flyer_repair_data,recovered_player_data)
fix_corrupted_dinos(data,orig_player_data,recovered_player_data) #fix greyed out dinos in obelisk
export_data_to_csv(data,csv_name_write) #export used database