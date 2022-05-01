'''
Useful for sending one or multiple messages to AWS SQS.Especially useful for those using Windows OS.
The application is build using PySimpleGUI. 
It expects you have setup the aws id/key in
Linux:   /home/[username]/.aws
Windows: /Users/[username]/.aws

'''

import PySimpleGUI as sg
import boto3
from botocore.config import Config
from boto3.session import Session
import threading
import time
#import datetime
from datetime import datetime,timedelta
import sys

session = boto3.session.Session()

distribution_list_data=[]
distribution_data=[]

sg.theme('Reddit')

#-----------------GUI Layout--------------------------------    

Console =[
    [sg.Text("Console")],
    [sg.Multiline(size=(48, 14),key="-CONSOLEMSG-",disabled=True)],
    [sg.B("Clear Console",size=(20, 1)),sg.B("Save Console",size=(21, 1))]
    ]

frame_layout = [
                  [sg.T('Id:'), sg.Text("",size=(45, 1),key="-text_id-"),sg.T(' Status:'), sg.Text("",size=(25, 1),key="-text_status-")],
                  [sg.T('Domain Name:'), sg.Text("",size=(50, 1),key="-text_domainname-")],
                  [sg.T('LastModifiedTime:'), sg.Text("",size=(60, 1),key="-text_lastmodifiedtime-")],
                  [sg.T('Logging:'), sg.Text("",size=(60, 1),key="-text_log-")],
                  [sg.T('Enabled:'), sg.Text("",size=(60, 1),key="-text_enabled-")],
                  [sg.T('HttpVersion:'), sg.Text("",size=(60, 1),key="-text_httpversion-")],
                  [sg.T('IsIPV6Enabled:'), sg.Text("",size=(60, 1),key="-text_ipv6-")],
                  [sg.T('InProgressInvalidationBatches:'), sg.Text("",size=(50, 1),key="-text_inprogress-")],
                  [sg.T('ARN:'), sg.Text("",size=(50, 1),key="-text_arn-")]
                 ]

Desc =[
       [sg.Frame('Description', frame_layout, font='Any 12', title_color='blue')]
       #,[sg.Multiline(size=(82, 12),key="-CONSOLEMSG1-",disabled=True)]
       ]




dist =[
       [sg.Text("Enter Distribution ID"),sg.InputText(key="-DistID-",size=(65, 1)), sg.B("Display Distribution",size=(25, 1)), sg.B("Show All",size=(30, 1)) ],
    [sg.Table(values=distribution_list_data,key="_DIST_", headings=['ID', 'Domain Name','Description','Status','Enabled','Last modified'],auto_size_columns=False, col_widths=[27, 30, 30],  num_rows=15,justification='left',right_click_menu=['&Right', ['Invalidate', 'Disable','Enable', 'Delete','Refresh']],enable_events=True )]
    ]

sqs_layout = [
    [
     sg.Column(dist)],      
     [
      sg.Column(Desc,size=(700, 270))
       ,sg.VSeperator(),
       sg.Column(Console)
      ]   
]


config =[
    [sg.Text('Enter Your AWS Id',size=(30, 1)), sg.InputText(key="-AWSID-",size=(30, 1))],
    [sg.Text('Enter Your AWS Key',size=(30, 1)), sg.InputText(key="-AWSKEY-",size=(30, 1))],
    [sg.Text('Enter Your Default Region',size=(30, 1)), sg.InputText(key="-DEFREGION-",size=(30, 1))],
    [sg.B("Reset",size=(28, 1)),sg.B("Connect",size=(27, 1))]
    ]

config_layout = [[sg.Column(config)]]

tabgrp = [[sg.TabGroup([[sg.Tab('Config', config_layout)],[sg.Tab('Cloudfront', sqs_layout)]])]]  

#--------------AWS SQS specific Functions--------------------------------------

#get list of all the available queues in a region

def get_distribution_list(REGION_NAME,window):
    REGION_CONFIG = Config(
    region_name = REGION_NAME,
    signature_version = 'v4',
    retries = {
        'max_attempts': 3
        }
    )
    try:
        CLIENT = session.client('cloudfront', config=REGION_CONFIG)
        
        response = CLIENT.list_distributions(
            MaxItems='100'
            )
        distribution_list_data.clear()
        for item in response['DistributionList']['Items']:
            distribution_list_data.append([item['Id'], item['DomainName'], item['Comment'], item['Status'], item['Enabled'], item['LastModifiedTime']])
        return distribution_list_data
    except Exception as e:
        return(e)


def get_distribution_detail(REGION_NAME,ID,window):
    REGION_CONFIG = Config(
    region_name = REGION_NAME,
    signature_version = 'v4',
    retries = {
        'max_attempts': 3
        }
    )
    try:
        CLIENT = session.client('cloudfront', config=REGION_CONFIG)
        
        response = CLIENT.get_distribution(
            Id=ID
            )
        return response
        
    except Exception as e:
        return(e)    



def update_distribution(REGION_NAME,ID,enable_state,window):
    REGION_CONFIG = Config(
    region_name = REGION_NAME,
    signature_version = 'v4',
    retries = {
        'max_attempts': 3
        }
    )
    try:
        CLIENT = session.client('cloudfront', config=REGION_CONFIG)
        
        distribution_config_response = CLIENT.get_distribution_config(Id=ID)
        #print(distribution_config_response)
        
        distribution_config = distribution_config_response['DistributionConfig']
        distribution_etag = distribution_config_response['ETag']
        distribution_config_enabled = distribution_config_response['DistributionConfig']['Enabled']
        
        
        if enable_state is True: #check if user requested to enable distribution
            if distribution_config_enabled is False:
                distribution_config_response['DistributionConfig']['Enabled'] = True
                distribution_config_response = CLIENT.update_distribution(DistributionConfig=distribution_config,
                                                                      Id=ID,
                                                                      IfMatch=distribution_etag)
        
        elif enable_state is False: #check if user requested to disable distribution
            if distribution_config_enabled is True: #check if distribution is enabled
                distribution_config_response['DistributionConfig']['Enabled'] = False
                distribution_config_response = CLIENT.update_distribution(DistributionConfig=distribution_config,
                                                                          Id=ID,
                                                                          IfMatch=distribution_etag)
        else:
            print("ooooops")
        
        window.write_event_value('-WRITE-',distribution_config_response)

    except Exception as e:
        window.write_event_value('-WRITE-',e)



def create_invalidation(REGION_NAME,ID, window):
    REGION_CONFIG = Config(
    region_name = REGION_NAME,
    signature_version = 'v4',
    retries = {
        'max_attempts': 3
        }
    )
    try:
        CLIENT = session.client('cloudfront', config=REGION_CONFIG)
        invalidate_response = CLIENT.create_invalidation(
            DistributionId=ID,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': [
                        '/*'
                    ]
                },
                'CallerReference': str(time.time()).replace(".", "")
            }
        )
        invalidation_id = invalidate_response['Invalidation']['Id']
        window.write_event_value('-WRITE-',"The invalidation id is: "+ invalidation_id)
    except Exception as e:
        window.write_event_value('-WRITE-',e)


def delete_distribution(REGION_NAME,ID, window):
    REGION_CONFIG = Config(
    region_name = REGION_NAME,
    signature_version = 'v4',
    retries = {
        'max_attempts': 3
        }
    )
    
    try:
        CLIENT = session.client('cloudfront', config=REGION_CONFIG)
        
        distribution_config_response = CLIENT.get_distribution_config(Id=ID)
        
        distribution_config = distribution_config_response['DistributionConfig']
        distribution_etag = distribution_config_response['ETag']
        distribution_config_enabled = distribution_config_response['DistributionConfig']['Enabled']
        
        if distribution_config_enabled is False:
            delete_distribution_response = CLIENT.delete_distribution(Id=ID, IfMatch=distribution_etag)
            window.write_event_value('-WRITE-',"Deleteing Distribution Completed "+ delete_distribution_response)
        else:
            distribution_config_response['DistributionConfig']['Enabled']=False
            distribution_config_response = CLIENT.update_distribution(
                DistributionConfig=distribution_config, 
                Id=ID, 
                IfMatch=distribution_etag)
        
            #wait for distribution to disable....
            window.write_event_value('-WRITE-',"It can take a while to disable distribution....")
            timeout_mins=30 
            wait_until = datetime.now() + timedelta(minutes=timeout_mins)
            notFinished=True
            distribution_etag=""
            while(notFinished):
                if wait_until < datetime.now(): #timeout
                    window.write_event_value('-WRITE-',"Distribution took too long to disable. Exiting")
                    sys.exit(1)
                
                distribution_status=CLIENT.get_distribution(Id=ID)
                if(distribution_status['Distribution']['DistributionConfig']['Enabled']==False and distribution_status['Distribution']['Status']=='Deployed'):
                    distribution_etag=distribution_status['ETag']
                    notFinished=False
                
                window.write_event_value('-WRITE-',"Disable not completed yet. Sleeping 30 seconds....")
                time.sleep(30) 
        
            delete_distribution_response= CLIENT.delete_distribution(Id=ID, IfMatch=distribution_etag)
            window.write_event_value('-WRITE-',"Deleteing Distribution Completed "+ delete_distribution_response)
    except Exception as e:
        window.write_event_value('-WRITE-',e)

def dist_list_worker_thread(region_name, window):
    try:
        data=[] #data=[]
        data = get_distribution_list("ap-southeast-2",window)
        window["_DIST_"].update(data)                
    except Exception as e:
        window.write_event_value('-WRITE-',e)
    
def dist_detail_worker_thread(region_name, ID, window):
    try:
        distribution_data.clear()
        data = get_distribution_detail("ap-southeast-2",ID,window)
                  
        distribution_data.append([data['Distribution']['Id'],data['Distribution']['DomainName'],
                                  data['Distribution']['ARN'],data['Distribution']['Status'],
                                  data['Distribution']['LastModifiedTime'],
                                  data['Distribution']['DistributionConfig']['Logging']['Enabled'],
                                  data['Distribution']['DistributionConfig']['Enabled'],
                                  data['Distribution']['DistributionConfig']['HttpVersion'],
                                  data['Distribution']['DistributionConfig']['IsIPV6Enabled'],
                                  data['Distribution']['InProgressInvalidationBatches']
                                  ])
        
        window["-text_id-"].update(data['Distribution']['Id'])
        window["-text_domainname-"].update(data['Distribution']['DomainName'])
        window["-text_arn-"].update(data['Distribution']['ARN'])
        window["-text_status-"].update(data['Distribution']['Status'])
        window["-text_lastmodifiedtime-"].update(data['Distribution']['LastModifiedTime'])
        window["-text_inprogress-"].update(data['Distribution']['InProgressInvalidationBatches'])
        window["-text_log-"].update(data['Distribution']['DistributionConfig']['Logging']['Enabled'])
        window["-text_enabled-"].update(data['Distribution']['DistributionConfig']['Enabled'])
        window["-text_httpversion-"].update(data['Distribution']['DistributionConfig']['HttpVersion'])
        window["-text_ipv6-"].update(data['Distribution']['DistributionConfig']['IsIPV6Enabled'])                
    except Exception as e:
        window.write_event_value('-WRITE-',e)
    


#-----------------Main function------------------------------------
def main():
    
    window = sg.Window('AWS Cloudfront Manager', tabgrp) #layout
    
    while True: # The Event Loop
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
        #---------Connection Tab-----------------------------
        if event == 'Reset':
            try:
                window["-AWSID-"].update("")
                window["-AWSKEY-"].update("")
                window["-DEFREGION-"].update("")
                window["-AWSID-"].SetFocus(force = True)
            except Exception as e:
                sg.popup(e)
        
        if event == 'Connect':
            try:
                global session
                
                if values['-DEFREGION-'] == "":
                    sg.popup("Region Field is missing")
                elif values['-AWSID-'] == "":
                    sg.popup("AWS ID Field is missing")
                elif values['-AWSKEY-'] == "":
                    sg.popup("AWS KEY Field is missing")
                else:
                    session = Session(region_name=values['-DEFREGION-'], aws_access_key_id=values['-AWSID-'],
                                  aws_secret_access_key=values['-AWSKEY-'])
                    #need to validate if connection is successful or not
                    sg.popup("Connection Established")
            except Exception as e:
                sg.popup(e)
        
        #---------Cloudfront Tab------------------------
        if event == 'Invalidate':
            try:
                get_distribution_list("ap-southeast-2",window)
            except Exception as e:
                window["-CONSOLEMSG-"].update(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) +": "+str(e)+"\n", append=True )
        
        if event == 'Refresh':
            window.refresh()
            threading.Thread(target=dist_list_worker_thread, args=("ap-southeast-2", window,),  daemon=True).start()
            
        
        if event == "Show All":
            try:
                threading.Thread(target=dist_list_worker_thread, args=("ap-southeast-2", window,),  daemon=True).start()
            except Exception as e:
                window["-CONSOLEMSG-"].update(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) +": "+str(e)+"\n", append=True )
        
              
        if event == '-WRITE-':
            window["-CONSOLEMSG-"].update(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) +": "+str(values['-WRITE-'])+"\n", append=True)
            
        
        if event == 'Disable':
            update_distribution("ap-southeast-2",distribution_data[0][0],False,window)

        if event == 'Enable':
            update_distribution("ap-southeast-2",distribution_data[0][0],True,window)
            
        
        if event == 'Delete':
            delete_distribution("ap-southeast-2",distribution_data[0][0], window)

        
        if event == 'Invalidate':
            create_invalidation("ap-southeast-2",distribution_data[0][0], window)

        if event == "_DIST_":
            try:
                data_selected = [distribution_list_data[row] for row in values[event]]
                threading.Thread(target=dist_detail_worker_thread, args=("ap-southeast-2",data_selected[0][0],window,),  daemon=True).start()
                
            except Exception as e:
                 window["-CONSOLEMSG-"].update(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) +": "+str(e)+"\n", append=True )

                
        if event == 'Save Console':
            try:
                file= open("output.txt", 'a+')
            except FileNotFoundError:
                file= open("output.txt", 'w+')
            file.write(str(window["-CONSOLEMSG-"].get()))
            file.close()
            sg.popup("File Saved")
        
        
        if event == 'Clear Console':
            window["-CONSOLEMSG-"].update("")
    window.close()

if __name__ == '__main__':
    main()