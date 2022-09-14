import requests
import json
import re
url = "http://tdjclient.zlongame.com/TDJ/android/android_gf_announcements.txt"
with requests.get(url) as r:
    r.encoding='utf-8'
    content = r.text
content=content.replace('\\n','<br>')
content=content.replace('<color=','<font color=').replace('/color>','/font>')
content=content.replace('	','')

#load string as json
text_list = json.loads(content)['noticelist']

s=requests.Session()

for text_dict in text_list:
    if re.search('未成年人防沉迷说明|公测今日开启|新服福利活动公告|公平运营公告',text_dict['name']) == None:
        year=2022
    else:
        year=2021


    time=f'{year}{text_dict["month"]:0>2}{text_dict["day"]:0>2}'
    name=f'{time}{text_dict["name"]}'
    content=f'{{{{公告\n|标题={text_dict["title"]}\n|时间={time}\n}}}}\n{text_dict["context"]}'

    # get content from wiki

    with s.get(f'https://wiki.biligame.com/tdj/api.php?action=parse&page=${name}&prop=wikitext&format=json') as r:
        r.encoding='utf-8'
        old_content = r.json()
        if old_content['error']:
            print(f'{name}不存在')
            print(old_content)
        elif old_content['parse']['wikitext']['*'] == content:
            print(f'{name}内容相同')
        else:
            print(f'{name}内容不同')