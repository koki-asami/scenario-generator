import argparse
import os
import time
from pathlib import Path

import numpy as np
import openai
import pandas as pd

# set api key
openai.api_key = os.environ['OPENAI_API_KEY']
# fix seed
np.random.seed(123)


class RecoveryStateGenerator:
    def __init__(
            self,
            recovery_state=['緊急対応期', '応急復旧期', '本格復旧準備期', '本格復旧期', '復旧完了'],
    ):
        self.thres = 0.1
        self.delta = 0.01
        self.recovery_state = recovery_state

    def __call__(self):
        if np.random.rand() < self.thres:
            print(f'\nMove to next state: \
                  {self.recovery_state[0]} -> {self.recovery_state[1]}')
            current_recovery_state = self.recovery_state.pop(0)
            self.thres = 0.1
        else:
            current_recovery_state = self.recovery_state[0]
            self.thres += self.delta
        return current_recovery_state


class ScenarioGenerator():
    def __init__(self):
        # set initial instruction message
        status = """
            # 命令書
            あなたは災害復旧における「人の往来」に関するイベントを生成する災害シナリオジェネレーターです。
            下記の時期ごとに発生するイベントはことなりますので、入力にある時期に応じて適切なイベントを生成してください。
            出力はイベント名のみにし、不要な説明は省いてください
            # 災害発生時期
            - 緊急対応期
            - 応急復旧期
            - 本格復旧準備期
            - 本格復旧期
            # 出力例
            ## 緊急対応期の場合
            通学の再開
            ## 応急復旧期の場合
            交通の再開
            物流の再開
            避難所からの帰宅
            避難所から一時提供表住宅への移動
            公営住宅への移動
            ## 本格復旧準備期の場合
            仮設住宅への移動
            通勤の再開
            ## 本格復旧期の場合
            仮設住宅からの帰宅
        """
        self.prefix = {
            'role': 'system',
            'content': status,
        }
        # create event state
        self.thres = 0.1
        self.delta = 0.01
        self.prev_events = []
        self.event = None
        self.prev_recovery_state = None

    def __call__(self, disaster_scale='中規模', recovery_state='緊急対応期', number_of_event=1):
        # check whether tp generate next event
        move2next_recovery_state = self.prev_recovery_state != recovery_state
        move2next_event = np.random.rand() < self.thres

        if move2next_recovery_state or move2next_event:
            input_ = f"""
                {disaster_scale}災害における{recovery_state}に起こりうるイベント名を{number_of_event}個出力してください。
                ただし、過去に出力した以下のイベントは出力しないでください。
                過去に出力したイベント: {self.prev_events}
                出力はイベント名のみにし、不要な説明は省いてください。
            """
            # self.messages.append({"role": "user", "content": input_})
            self.messages = [self.prefix, {'role': 'user', 'content': input_}]
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=self.messages,
                temperature=0.1,
            )
            self.event = response['choices'][0]['message']['content']
            # self.messages.append({'role': 'system', 'content': self.event})
            self.prev_events.append(self.event)
            print(f'\nMove to next event: {self.prev_events[-1]} -> {self.event}')
            self.thres = 0.1
        else:
            self.thres += self.delta
        self.prev_recovery_state = recovery_state
        return self.event


def generate_scenario(out_path):
    # create output directory
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f'./{out_path.parent}/{out_path.stem}.csv')

    s = RecoveryStateGenerator()
    e = ScenarioGenerator()
    df = pd.DataFrame(columns=['day', 'recovery_state', 'event'])
    recovery_state = None
    day = 0
    while recovery_state != '復旧完了':
        recovery_state = s()
        event = e(recovery_state=recovery_state)
        print(f"""
# Day {day}
## Recovery State: {recovery_state}
### Event: {event}
        """)
        df.loc[len(df)] = [day, recovery_state, event]
        day += 1
        time.sleep(0.1)
    print(df)
    # save dataframe into csv
    df.to_csv(f'./{out_path.parent}/{out_path.stem}.csv')


if __name__ == '__main__':
    # Initialize parser
    parser = argparse.ArgumentParser()
    # Adding optional argument
    parser.add_argument('-o', '--out_path', default='output/scenario', help='Output path')
    args = parser.parse_args()

    generate_scenario(out_path=Path(args.out_path))
