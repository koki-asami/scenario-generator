import os
import openai
import time

from langchain.document_loaders import DirectoryLoader, PyPDFLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS


openai.api_key = os.environ['OPENAI_API_KEY']
REFERENCE_DB_DIR = "./faiss_db"
LOCATION_DB_DIR = "./faiss_location_db"

print("Loading documents...")
loader = DirectoryLoader('evacuation_training/', glob="**/*.pdf", show_progress=True, loader_cls=PyPDFLoader, use_multithreading=True)
docs = loader.load()
documents = [doc.page_content for doc in docs]
print("Loaded documents.")

# print("Splitting documents...")
# chunk_size = 600
# chunk_overlap = 4

# r_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=chunk_size,
#         chunk_overlap=chunk_overlap
#         )
# documents = r_splitter.split_text(docs[0].page_content)

# print("Creating database")
# db = FAISS.from_documents(docs, OpenAIEmbeddings())
# db.save_local(REFERENCE_DB_DIR)
# print("Created and saved database.")

# ## load location info
# print("Loading location info...")
# loader = DirectoryLoader('evacuation_training/', glob="枚方市地名一覧/*.csv", show_progress=True, loader_cls=CSVLoader, use_multithreading=True)
# docs = loader.load()
# documents = [doc.page_content for doc in docs]
# print("Loaded documents.", documents)

# print("Splitting documents...")
# chunk_size = 600
# chunk_overlap = 4

# r_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=chunk_size,
#         chunk_overlap=chunk_overlap
#         )
# documents = r_splitter.split_text(docs[0].page_content)

# print("Creating database")
# db = FAISS.from_documents(docs, OpenAIEmbeddings())
# db.save_local(LOCATION_DB_DIR)
# print("Created and saved database.")

print("Loading database...")
db = FAISS.load_local(REFERENCE_DB_DIR, OpenAIEmbeddings())
location_db = FAISS.load_local(LOCATION_DB_DIR, OpenAIEmbeddings())
location_retriever = location_db.as_retriever()

# print("\n地名一覧を教えてください")
# query = "地名を全て教えてください"
# docs = location_retriever.get_relevant_documents(query)
# for i in range(len(docs)):
#     print(docs[i].page_content)

with open('evacuation_training/枚方市地名一覧/output.csv', 'r') as file:
    locations = file.read().splitlines()

from langchain.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["references", "locations"],
    template="""
# 命令書
- あなたは自治体にて避難訓練をシナリオを生成する専門家です
- あなたの役割は災害対応シミュレーション(主に地震)における状況付与を時系列に作成することです

# 制約条件
- 出力はcsv形式でお願いします
- カラムは以下の通りです
 - 時間, 状況, 住所, 被害状況, 事象（水道）, 事象（下水）, 事象（公共施設）, 事象（道路）, 事象（住宅）, 事象（その他）,  対応部署, 理想的な対応例, 注意事項, 
- 人の名前部分は<名前>としてください
   - 例) 大谷次長 -> <名前>次長
- 出力は時系列にお願いします
 - 時間は1分単位でお願いします
- 表以外の出力はしないでください(説明等も不要です)
- timestepは最低でも15個は出力してください
- 出力には状況に対する理想的な対応も可能な限り詳細に記載してください

# 参考データ
- 以下のデータは実際に自治体で行われた、状況付与訓練のデータです。これらを参考に生成してください
 - 時間の粒度は参照してください
 - また、状況の変化についても参考にしてください
 - 出力は表形式でお願いします
 - 参考データ: {references}
- こちらのデータは枚方市の地名一覧です。これらを参考に地域に関連する依頼イベントを生成してください
 - 参考データ: {locations}

""",
)

retries = 10
while retries > 0:
    start_time = time.time()
    try: 
        response = openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": prompt.format(references=documents, locations=locations)},
            ],
            max_tokens=128000,
            # request_timeout=15,  
            temperature=0.3,
        )
        print(f"Time taken: {time.time() - start_time}")
        print(response.choices[0]["message"]["content"].strip())

        # save response in md file
        with open(f"scenarios_20231212/evacuation_training_scenario_{i}.csv", "w") as f:
            f.write(response.choices[0]["message"]["content"].strip())
        retries -= 1
    except Exception as e:    
         if e: 
             print(e)   
             print('Timeout error, retrying...')    
                 
             time.sleep(5)    
         else:    
             raise e
