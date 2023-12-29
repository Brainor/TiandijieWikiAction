import json
import re
import sys

import requests

URL = "https://wiki.biligame.com/tdj/api.php"
s = requests.Session()


def init_session():
    # 初始化cookies
    s.cookies.set("SESSDATA", SESSDATA, domain=".biligame.com", secure=True, rest={"HttpOnly": True})
    s.cookies.set("DedeUserID", "1381806", domain=".biligame.com")

    # Step1: Retrieve login token
    PARAMS_0 = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json",
    }
    # if 'gamecenter_wiki_LoggedOut' in s.cookies.keys():
    #     s.cookies.clear(name='gamecenter_wiki_LoggedOut',domain='wiki.biligame.com',path='/tdj/')
    try:
        R = s.get(url=URL, params=PARAMS_0)
        LOGIN_TOKEN = R.json()["query"]["tokens"]["logintoken"]
    except Exception as e:
        print(R.text)
        raise e

    PARAMS_1 = {
        "action": "login",
        "lgname": "1381806@BrainorActions",
        "lgpassword": LGPASSWORD,
        "format": "json",
    }
    try:
        R = s.post(URL, data=PARAMS_1 | {"lgtoken": LOGIN_TOKEN})
        if R.json()["login"]["result"] != "Success":
            print(R.json())
            raise Exception("login failed")
    except Exception as e:
        print(R.text)
        raise e


def wiki_check_exists(name: str):
    # get content from wiki
    PARAMS_0 = {
        "action": "parse",
        "page": name,
        "prop": "wikitext",
        "format": "json",
    }
    try:
        R = s.get(url=URL, params=PARAMS_0)
        R.encoding = "utf-8"
        response = R.json()
    except Exception as e:
        print(R.text)
        raise e
    return response


def wiki_edit_page(name: str, content: str, modify=True, **kargs):
    # get token
    PARAMS_0 = {"action": "query", "meta": "tokens", "format": "json"}
    try:
        R = s.get(url=URL, params=PARAMS_0)
        CSRF_TOKEN = R.json()["query"]["tokens"]["csrftoken"]
    except Exception as e:
        print(R.text)
        raise e

    # edit wiki
    PARAMS_1 = {
        "action": "edit",
        "title": name,
        "format": "json",
        "text": content,
        "token": CSRF_TOKEN,
        f'{"minor" if modify else "notminor"}': "",
        "summary": "内容扩充" if modify else "创建页面",
    } | kargs
    try:
        R = s.post(URL, data=PARAMS_1)
        R.encoding = "utf-8"
        edit_result = R.json()
    except Exception as e:
        print(R.text)
        raise e
    if "error" in edit_result:
        print(f"{name} 编辑失败")
        print(edit_result)
    else:
        print(f"{name} 编辑成功")


def wiki_file_sha1(name: str):
    """
    https://wiki.biligame.com/tdj/特殊:ApiSandbox#action=query&format=json&prop=imageinfo&titles=File:立绘_千秋叶.png&iiprop=sha1
    """
    PARAMS_0 = {
        "action": "query",
        "prop": "imageinfo",
        "titles": f"File:{name}",
        "iiprop": "sha1",
        "format": "json",
    }
    try:
        R = s.get(url=URL, params=PARAMS_0)
        response = R.json()
    except Exception as e:
        print(R.text)
        raise e
    return response


def check_and_compare_file(name: str, remote_bfile: bytes, modify):
    import hashlib

    # check file exists
    # wiki_file_loc = f'{URL.removesuffix("/api.php")}/Special:FilePath/{name}'

    if modify:
        old_content = wiki_file_sha1(name)
        if "-1" in old_content["query"]["pages"]:
            flag = "not exist"
        else:
            wiki_sha1 = list(old_content["query"]["pages"].values())[0]["imageinfo"][0]["sha1"]
            remote_sha1 = hashlib.sha1(remote_bfile).hexdigest()
            if wiki_sha1 == remote_sha1:
                flag = "exist"
                remote_bfile = None
            else:
                flag = "different"
    else:
        flag = "not exist"
    return flag


def wiki_upload_files(image_list: list[tuple[str, bytes] | str], basename: str, modify=True, **kargs):
    # get token
    PARAMS_0 = {
        "action": "query",
        "meta": "tokens",
        "format": "json",
    }
    try:
        R = s.get(url=URL, params=PARAMS_0)
        CSRF_TOKEN = R.json()["query"]["tokens"]["csrftoken"]
    except Exception as e:
        print(R.text)
        raise e

    # upload files
    PARAMS_1 = {
        "action": "upload",
        "token": CSRF_TOKEN,
        "format": "json",
    } | kargs

    replace_file = []  # 重复文件记录, 需要修改后续content内容
    for bfile in image_list:
        if isinstance(bfile, str):
            continue
        flag = check_and_compare_file(bfile[0], bfile[1], modify)
        match flag:
            case "exist":
                continue
            case "different":
                PARAMS_2 = {"ignorewarnings": "1", "filename": bfile[0]}
            case "not exist":
                PARAMS_2 = {"filename": bfile[0]}
        FILE = {"file": (bfile[0], bfile[1], "multipart/form-data")}
        try:
            R = s.post(URL, data=PARAMS_1 | PARAMS_2, files=FILE)
            R.encoding = "utf-8"
            edit_result = R.json()
        except Exception as e:
            print(R.text)
            raise e
        match edit_result["upload"]["result"]:
            case "Success":
                print(f"{bfile[0]} 上传成功")
            case "Warning":
                if "duplicate" in edit_result["upload"]["warnings"]:  # 重复文件, 文件名不同 {'upload': {'result': 'Warning', 'warnings': {'duplicate': ['全新玩法「溯念之门」即将开启.27.png']}, 'filekey': '1allyddf5n40.jujva0.144100.png', 'sessionkey': '1allyddf5n40.jujva0.144100.png'}}
                    new_file = edit_result["upload"]["warnings"]["duplicate"][0]
                    replace_file.append((bfile[0], new_file))
                    print(f"{bfile[0]} 已存在: {new_file}")
                else:
                    print(edit_result)
                    print(f"{bfile[0]} 上传失败")
            case _:
                print(edit_result)
                print(f"{bfile[0]} 上传失败")
    return replace_file


def get_announcement_list():
    url = "http://tdjclient.zlongame.com/TDJ/android/android_gf_announcements.txt"
    try:
        R = requests.get(url)
        R.encoding = "utf-8"
        content = R.text
    except Exception as e:
        print(R.text)
        raise e
    content = content.replace("\\n", "<br>")
    content = content.replace("<color=", "<font color=").replace("/color>", "/font>")
    content = content.replace("	", "")

    # load string as json
    text_list = json.loads(content)["noticelist"]
    return text_list


def edit_wiki_announcement(text_list):
    for text_dict in text_list:
        try:
            year = re.search(r"(\d{4})年\d+月\d+日\s*$", text_dict["context"]).group(1)
        except AttributeError:
            year = 2023

        time = f'{year}{text_dict["month"]:0>2}{text_dict["day"]:0>2}'
        name = f'{time}{text_dict["name"]}'
        content = f'{{{{公告\n|标题={text_dict["title"]}\n|时间={time}\n}}}}\n{text_dict["context"]}'

        old_content = wiki_check_exists(name)
        # if old_content has key 'error'
        if "error" in old_content:
            print(f"{name} 不存在")
            wiki_edit_page(name, content, False)
        elif old_content["parse"]["wikitext"]["*"] == content:
            print(f"{name} 内容相同")
        else:
            print(f"{name} 内容不同")
            wiki_edit_page(name, content)


def get_news_list():
    from bs4 import BeautifulSoup

    def remote_content(origin_loc) -> bytes | str:
        try:
            R = s.get(origin_loc, stream=False)
            if len(R.content) <= 7 * 1024 * 1024:
                return R.content
            else:
                return origin_loc
        except Exception as e:
            print(R.text)
            raise e

    text_list = []
    recognized_tags = ["abbr", "b", "bdi", "bdo", "blockquote", "br", "caption", "cite", "code", "data", "dd", "del", "dfn", "div", "dl", "dt", "em", "h1", "hr", "i", "ins", "kbd", "li", "link", "mark", "meta", "ol", "p", "nowiki", "q", "rp", "rt", "ruby", "s", "samp", "small", "span", "strong", "sub", "sup", "table", "td", "th", "time", "tr", "u", "ul", "var", "wbr"]
    for index in ["index", "index_2"]:
        try:
            R = requests.get(f"https://www.zlongame.com/jx/tdjInfoNews/{index}.html")
            R.encoding = "utf-8"
            text_list += R.json()
        except Exception as e:
            print(R.text)
            raise e
    for content in text_list:
        image_list = []  # 每个元素为(name, bfile)|str
        try:
            R = requests.get(f'https://www.zlongame.com{content["url"]}')
            R.encoding = "utf-8"
            html_text = R.text
        except Exception as e:
            print(R.text)
            raise e
        # get innerhtml of '.article_title_wrap' of html_text using BeautifulSoup
        soup = BeautifulSoup(str(BeautifulSoup(html_text, "html.parser").find(class_="article_text")), "html.parser")
        soup.div.unwrap()
        # 去掉不识别的tag
        flag = 0
        while flag == 0:
            flag = 1
            for descendant in soup.descendants:
                if descendant.name and descendant.name not in recognized_tags:
                    flag = 0
                    if descendant.name == "img":
                        bfile = remote_content(descendant["src"])
                        # image_list.append(bfile)
                        if isinstance(bfile, bytes):
                            format = re.search(r"\.[^.]+$", descendant["src"]).group()
                            name = f'{content["title"]}.{len(image_list)}{format}'
                            option = ""
                            image_list.append((name, bfile))
                            if "style" in descendant.attrs.keys():
                                style_text = descendant["style"]
                                if result := re.search(r"width:\s*(\d+)", style_text):
                                    option += result.group(1)
                                if result := re.search(r"height:\s*(\d+)", style_text):
                                    option += "x" + result.group(1)
                                if option:
                                    option += "px"
                            img_text = f"[[File:{name}|{option}|link=]]"
                            descendant.replace_with(img_text)
                        else:  # 文件太大, 直接外链
                            image_list.append(bfile)
                            # create a span tag with class and text
                            span = soup.new_tag("span", attrs={"class": "plainlinks"})
                            span.string = f'[{descendant["src"]} 图像链接]'
                            descendant.replace_with(span)
                    else:
                        descendant.unwrap()

        content["html_text"] = str(soup).strip() # 最后可能会有换行符会被bwiki去掉
        content["image_list"] = image_list

    return text_list


def edit_wiki_news(text_list):
    for text_dict in text_list:
        year, month, day = re.search(r"^(\d+)\.(\d+)\.(\d+)", text_dict["time"]).group(1, 2, 3)
        time = f"{year}{month:0>2}{day:0>2}"
        content = f'{{{{文章戳\n|文章名={text_dict["title"]}\n<!-- 文章名请填写文章标题，可与词条名不同 -->\n|更新时间={time}\n<!-- 时间格式为YYMMDD 例：20200925 -->\n|文章分类=攻略\n<!-- 公告/攻略/视频/同人等 任选其一 -->\n|是否原创=\n<!-- 请填写是或者否 -->\n|作者=\n<!-- 请填写作者名字 -->\n|哔哩哔哩UID=\n<!-- 选填，请填写哔哩哔哩UID号 -->\n|NGA用户ID=\n<!-- 选填，请填写NGA论坛用户ID -->\n|贴吧昵称=\n<!-- 选填，请填写贴吧昵称 -->\n|原文地址=https://www.zlongame.com{text_dict["url"]}\n<!-- 授权转载文章请务必填写原文URL链接地址 -->\n}}}}\n<!-- 以下请编辑正文 -->\n{text_dict["html_text"]}'

        # get content from wiki
        PARAMS_0 = {
            "action": "parse",
            "page": text_dict["title"],
            "prop": "wikitext",
            "format": "json",
        }
        try:
            R = s.get(url=URL, params=PARAMS_0)
            R.encoding = "utf-8"
            old_content = R.json()
            # if old_content has key 'error'
        except Exception as e:
            print(R.text)
            raise e
        if "error" in old_content:
            print(f'{text_dict["title"]} 不存在')
            replace_file = wiki_upload_files(text_dict["image_list"], text_dict["title"], modify=False)
            if replace_file:
                for name, new_name in replace_file:
                    content = content.replace("File:" + name, "File:" + new_name)
            wiki_edit_page(text_dict["title"], content, modify=False)
        elif old_content["parse"]["wikitext"]["*"] == content:
            print(f'{text_dict["title"]} 内容相同')
        else:
            print(f'{text_dict["title"]} 内容不同')
            replace_file = wiki_upload_files(text_dict["image_list"], text_dict["title"])
            if replace_file:
                for name, new_name in replace_file:
                    content = content.replace("File:" + name, "File:" + new_name)
            if old_content["parse"]["wikitext"]["*"] != content:
                wiki_edit_page(text_dict["title"], content)
            else:
                print(f'{text_dict["title"]} 调整后内容相同')


def job_announcement():
    text_list = get_announcement_list()
    edit_wiki_announcement(text_list)


def job_news():
    text_list = get_news_list()
    edit_wiki_news(text_list)


if __name__ == "__main__":
    LGPASSWORD, SESSDATA = sys.argv[2:4]
    init_session()
    job_announcement()
    if sys.argv[1] == "0 16 * * 4":  # 周四更新
        print("周四更新攻略")
        job_news()
    else:
        print("not 周四")
