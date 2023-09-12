from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import PyPDFLoader
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
import time
import os
import openai
import datetime


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 1000,
    chunk_overlap  = 20,
    length_function = len,
)

def process_pdf(pdf_path):
    date = datetime.date.today().strftime('%Y/%m/%d')
    print(date)
    
    loader = PyPDFLoader(pdf_path)
    pages = loader.load_and_split()

    state_of_the_union = "".join([x.page_content for x in pages])
    texts = text_splitter.create_documents([state_of_the_union])

    embeddings = OpenAIEmbeddings()
    filename = f"faiss_index/{pdf_path.split('/')[-1]}"  # チェックするファイル名
    if os.path.isdir(filename):
        vectorstore = FAISS.load_local(filename, embeddings)
    else:
        vectorstore = FAISS.from_documents(texts, embedding=embeddings)
    vectorstore.save_local(filename)

    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
    retrieval_chain_agent = ConversationalRetrievalChain.from_llm(llm, vectorstore.as_retriever(), return_source_documents=True)

    query = f'''
    この論文について重要なテーマを3つまでカンマ区切りで挙げてください。カンマ区切りの単語のリストのみを出力してください。
    '''
    chat_history = []

    result = retrieval_chain_agent({"question": query, "chat_history": chat_history})
    chat_history.append(query)
    chat_history.append(result)

    results = []
    topics = result["answer"].split(",")
    print(topics)

    if len(topics) < 2:
        raise Exception
    for t in topics:
        print(t)
        query = f'{t}について200字以上、1000字以内の日本語に要約してください。'
        time.sleep(10)
        result = retrieval_chain_agent({"question": query, "chat_history": []})
        print(result)
        results.append(result["answer"])

    status = '''
    あなたは熟練のコンサルタントです。与えられた文章について簡潔に説明するためのスライドを作成します。
    まず最初に、次のようなMarpのデザインテンプレートを使用したマークダウン形式で、カバースライドを作成してください。
    タイトルは論文のタイトルをそのまま使用してください。
    日付は今日の日付を使用してください。
    名前はユーザー名を使用してください。
    カバースライドは一枚のみで、これ以降はボディスライドを作成してください。
    """

    ---
    <!--
    class: title
    -->
    # { タイトル }
    ### { 日付 }
    ## D1 { 名前 }

    """
    ボディスライドは次のようなMarpのデザインテンプレートを使用し、マークダウン形式で表現して下さい。
    タイトルはトピックの内容をそのまま使用して下さい。もし、10字以上なら10字以下に短縮して下さい。
    概要は与えられた文章の内容についての要約を、箇条書きではなく50文字程度の文章で記述して下さい。
    キーワードの箇条書きは与えられた文章の内容の中で重要な単語を3つ以内で記載して下さい。
    説明はキーワードに対する説明を20時程度の文章で記載して下さい。
    """

    ---
    <!--
    class: body
    -->
    # { タイトル }
    ## { 概要 }
    - { キーワード }: { 説明 }

    """
    '''
    prefix = [
            {"role": "system", "content": status},
    ]

    slides = []
    data = f"""
    まず最初に、次のようなMarpのデザインテンプレートを使用したマークダウン形式で、カバースライドを日本語で作成してください。
    タイトルは{(pdf_path.split("/")[-1]).split(".")[0]}です。
    日付は{date}を使用してください。
    名前はユーザー名を使用してください。
    """
    comversation = [{"role": "user", "content": data}]
    messages = prefix + comversation
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature = 0,
    )
    time.sleep(10)
    answer = response["choices"][0]["message"]["content"]
    slides.append(answer)
    for r in results:
        data = f"""
    次に与えられる文章の内容について上記で与えられたボディスライドのテンプレートを使用し、Marpによるマークダウン形式でスライドを日本語で作成してください。
    必要に応じてスライドは2枚以上に分割してください。スライドを分割する場合はタイトルと概要の内容はそのままに、キーワードと説明の内容を分割してください。
    カバースライドは使用しないでください。
    {r}

        """
        comversation = [{"role": "user", "content": data}]
        messages = prefix + comversation
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature = 0,
        )
        time.sleep(10)
        answer = response["choices"][0]["message"]["content"]
        slides.append(answer)

    output_str = f"""---
marp: true
footer: "{date}"
size: 16:9
paginate: true
theme: template

"""

    # with open(output_path, "r") as file:
    #     test_output_str = file.readlines()
    # output_str = "".join(test_output_str)
    # print(output_str)
    for i in slides:
        output_str += i + "\n"

    output_path = f'download/{(pdf_path.split("/")[-1]).split(".")[0]}_slide.md'
    
    print(output_path)
    with open(output_path, "w") as file:
        file.write(output_str)
    
    os.system(f"npx @marp-team/marp-cli@latest --theme-set download/template.css --pdf {output_path} --allow-local-files -y")

    return (output_path.replace(".md", ".pdf"), output_str)
