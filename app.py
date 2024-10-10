import os
from flask import Flask, render_template, request, session, redirect, url_for
import os
from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 为了使用session，需要设置secret_key

# 设置OpenAI API密钥
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 属性键的映射
ATTRIBUTE_KEYS = {
    'intelligence': '智力',
    'appearance': '外貌',
    'health': '健康',
    'emotional_intelligence': '情商',
    'wealth': '财富',
    'reputation': '声望',
    'morality': '道德',
    'creativity': '创造力',
    'social_skills': '社交技能',
    'perseverance': '毅力'
}

# 定义初始属性范围，增加了“创造力”、“社交技能”、“毅力”等属性
INITIAL_ATTRIBUTES = {
    '智力': 50,
    '外貌': 50,
    '健康': 50,
    '情商': 50,
    '财富': 50,
    '声望': 0,
    '道德': 50,
    '创造力': 50,
    '社交技能': 50,
    '毅力': 50
}



# 定义属性的上限和下限
ATTRIBUTE_MIN = 0
ATTRIBUTE_MAX = 100

# 定义初始NPC列表，每个NPC有名字、关系和好感度
INITIAL_NPCS = [
    {'name': '父母', 'relation': '家庭', 'likability': 50},
    {'name': '老师', 'relation': '教育', 'likability': 50},
    {'name': '朋友', 'relation': '社交', 'likability': 50},
    {'name': '恋人', 'relation': '情感', 'likability': 50}
]

# 定义重大事件记录
MAJOR_EVENTS = []

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start_game', methods=['GET', 'POST'])
def start_game():
    if request.method == 'POST':
        # 打印表单数据以进行调试
        print(request.form)

        # 获取玩家选择的初始设定
        gender = request.form.get('gender')
        family = request.form.get('family')

        # 玩家分配初始属性点，总共500点，玩家可以自由分配
        total_points = 500
        allocated_attributes = {}
        for key, label in ATTRIBUTE_KEYS.items():
            value_str = request.form.get(key)
            if value_str is None:
                error = f"请分配属性点。"
                return render_template('start_game.html', error=error, attributes=ATTRIBUTE_KEYS)
            try:
                value = int(value_str)
            except ValueError:
                error = f"属性 {label} 的值无效，请输入数字。"
                return render_template('start_game.html', error=error, attributes=ATTRIBUTE_KEYS)
            allocated_attributes[label] = value
            total_points -= value

        if total_points != 0:
            error = "属性点分配总和必须为500，请重新分配。"
            return render_template('start_game.html', error=error, attributes=ATTRIBUTE_KEYS)

        # 设置初始状态
        session['age'] = 0  # 0岁
        session['attributes'] = allocated_attributes
        session['gender'] = gender
        session['family'] = family
        session['background'] = generate_background(family)
        session['history'] = []  # 记录每一轮的选择和事件
        session['npcs'] = INITIAL_NPCS.copy()  # 复制初始NPC列表
        session['major_events'] = []  # 重大事件列表
        return redirect(url_for('game'))
    else:
        return render_template('start_game.html', attributes=ATTRIBUTE_KEYS)


@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'attributes' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # 处理玩家的选择
        choice = request.form.get('choice')
        event = session.get('current_event')
        if event and choice is not None:
            choice = int(choice)
            selected_option = event['options'][choice]
            # 更新属性
            update_attributes(selected_option['effects'])
            # 更新NPC好感度
            update_npc_likability(selected_option.get('npc_effects', {}))
            # 记录重大事件
            major_event = selected_option.get('major_event')
            if major_event:
                session['major_events'].append(major_event)
            # 记录历史
            session['history'].append({
                'age': session['age'],
                'event': event['description'],
                'choice': selected_option['text'],
                'effects': selected_option['effects']
            })
            # 增加年龄
            session['age'] += 0.5  # 每一轮半年
        else:
            return redirect(url_for('index'))

    # 检查游戏结束条件
    if session['age'] >= 80 or session['attributes']['健康'] <= 0:
        return redirect(url_for('result'))

    # 生成新的事件
    event = generate_event()
    session['current_event'] = event
    return render_template('game.html', event=event, age=session['age'], attributes=session['attributes'], npcs=session['npcs'])

@app.route('/result')
def result():
    return render_template('result.html', history=session.get('history'), attributes=session.get('attributes'), major_events=session.get('major_events'))

def generate_background(family):
    # 根据玩家选择的家庭生成背景
    backgrounds = {
        'ordinary': '出生在一个普通家庭，父母都是勤劳的工薪族。',
        'wealthy': '出生在一个富裕家庭，父母是成功的企业家。',
        'rural': '出生在农村，家庭条件一般，父母是农民。',
        'scholar': '出生在一个书香门第，父母都是大学教授。',
        'artist': '出生在一个艺术家庭，父母是著名艺术家。'
    }
    return backgrounds.get(family, '出生在一个未知的家庭。')

def generate_event():
    # 使用OpenAI API生成事件
    age = session['age']
    attributes = session['attributes']
    background = session['background']
    gender = session['gender']
    npcs = session['npcs']
    major_events = session['major_events']

    # 构建NPC信息字符串
    npc_info = "\n".join([f"{npc['name']}（好感度：{npc['likability']}）" for npc in npcs])

    prompt = f"""
角色信息：
- 年龄：{age}岁
- 性别：{gender}
- 属性：
{"".join([f"- {key}：{value} " for key, value in attributes.items()])}
- 背景：{background}
- NPC关系：
{npc_info}
- 重大事件：{', '.join(major_events) if major_events else '无'}

请为该角色生成一个幽默、有趣且丰富的任务描述和3个不同的选择，每个选择需对属性和NPC好感度产生不同影响。任务需要考虑到角色的年龄、背景、属性、技能和NPC关系。

**请注意：**
- 所描述的任务需要考虑到角色的年龄、性别、属性、背景、NPC关系和重大事件。（生成的任务一定要符合角色的年龄，比如0岁的孩子不会走路、说话）
- 每一轮的任务都尽量不同，而不是针对某一个事物反复设计任务。
- 任务描述应包含幽默元素，如双关语、俏皮话或讽刺。
- 请仅返回以下格式的JSON，不要添加任何额外的文字或说明。
- 在JSON中，数值不要包含`+`号，只使用整数表示增减变化。
- 如果涉及到NPC，请在`npc_effects`中注明对哪个NPC产生影响。
- 可以加入技能学习或提升的选项。

返回格式示例：

{{
  "description": "任务描述",
  "options": [
    {{
      "text": "选项1描述",
      "effects": {{"智力": 5, "健康": -2}},
      "npc_effects": {{"父母": 5}},
      "major_event": "获得全国数学竞赛一等奖",
      "skills": {{"数学": 10}}
    }},
    {{
      "text": "选项2描述",
      "effects": {{"情商": 3, "财富": 2}},
      "npc_effects": {{"老师": -3}}
    }},
    {{
      "text": "选项3描述",
      "effects": {{"外貌": 2, "健康": 1}},
      "npc_effects": {{"朋友": 4}}
    }}
  ]
}}
    """

    # 调用OpenAI API
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # 使用您有权限的模型
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        # 获取返回的消息内容
        message = completion.choices[0].message.content

        print("AI Response:", message)

        # 解析返回的JSON
        import json
        event = json.loads(message)
        return event
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        # 如果出现错误，返回一个预设的事件
        return {
            "description": "你遇到了一个无法描述的奇怪事件。",
            "options": [
                {"text": "选择一，随遇而安。", "effects": {"健康": +0}},
                {"text": "选择二，奋力抵抗。", "effects": {"健康": -5}},
                {"text": "选择三，转身逃跑。", "effects": {"健康": -2}}
            ]
        }

def update_attributes(effects):
    for key, value in effects.items():
        if key in session['attributes']:
            session['attributes'][key] = max(ATTRIBUTE_MIN, min(ATTRIBUTE_MAX, session['attributes'][key] + value))
        else:
            # 如果是新技能，添加到属性中
            session['attributes'][key] = value

def update_npc_likability(npc_effects):
    for npc_name, change in npc_effects.items():
        for npc in session['npcs']:
            if npc['name'] == npc_name:
                npc['likability'] = max(0, min(100, npc['likability'] + change))
                break

if __name__ == '__main__':
    app.run(debug=True)
