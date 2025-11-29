# -*- coding: utf-8 -*-
import streamlit as st
import random
import time
import io
import csv
import json
import os

# ================= 設定與樣式 =================
AGE_GROUPS = ["低年級", "中年級", "高年級", "國中以上"]

st.set_page_config(page_title="聖誕節分類帽系統", layout="wide")

# ---- 全域按鈕變大一點（含分類鍵）----
st.markdown(
    """
    <style>
    div.stButton > button {
        font-size: 1.4rem;
        padding: 0.8rem 2.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 用來讓重整後還能保留資料的本地檔案
STATE_FILE = "sorting_state.json"


# ================= 檔案存取邏輯 =================
def save_state_to_file():
    data = {
        "theme": st.session_state.theme,
        "team_count": st.session_state.team_count,
        "team_size": st.session_state.team_size,
        "team_names": st.session_state.team_names,
        "balance_age": st.session_state.balance_age,
        "require_name": st.session_state.require_name,
        "students": st.session_state.students,
        "teams": st.session_state.teams,
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("save_state error:", e)


def load_state_from_file():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("load_state error:", e)
        return None


# ================= 狀態初始化與隊伍管理 =================
def ensure_team_names_length():
    """確保 team_names 長度跟 team_count 一致。"""
    n = st.session_state.team_count
    names = st.session_state.team_names
    if len(names) < n:
        for i in range(len(names), n):
            names.append(f"第{i+1}隊")
    elif len(names) > n:
        st.session_state.team_names = names[:n]


def rebuild_teams_from_names(keep_members: bool):
    """根據目前隊名重建 teams，必要時保留原成員。"""
    ensure_team_names_length()
    new_teams = [{"name": name, "members": []} for name in st.session_state.team_names]

    if keep_members and st.session_state.teams:
        name_to_team = {t["name"]: t for t in new_teams}
        for old in st.session_state.teams:
            for m in old.get("members", []):
                t = name_to_team.get(old["name"])
                if t is not None:
                    t["members"].append(m)

    st.session_state.teams = new_teams


def init_state():
    if "initialized" in st.session_state and st.session_state.initialized:
        return

    st.session_state.initialized = True

    # 預設值
    st.session_state.theme = "聖誕節分類帽分組系統"
    st.session_state.team_count = 3
    st.session_state.team_size = 100
    st.session_state.team_names = ["麋鹿隊", "雪人隊", "聖誕樹隊"]
    st.session_state.balance_age = True
    st.session_state.require_name = True
    st.session_state.students = []
    st.session_state.teams = []
    st.session_state.last_assignment = None

    # 嘗試從檔案載入
    data = load_state_from_file()
    if data:
        st.session_state.theme = data.get("theme", st.session_state.theme)
        st.session_state.team_count = int(data.get("team_count", st.session_state.team_count))
        st.session_state.team_size = int(data.get("team_size", st.session_state.team_size))
        st.session_state.team_names = data.get("team_names", st.session_state.team_names)
        st.session_state.balance_age = data.get("balance_age", st.session_state.balance_age)
        st.session_state.require_name = data.get("require_name", st.session_state.require_name)
        st.session_state.students = data.get("students", [])
        st.session_state.teams = data.get("teams", [])

    if not st.session_state.teams:
        rebuild_teams_from_names(keep_members=False)
    else:
        rebuild_teams_from_names(keep_members=True)


# ================= 核心邏輯：分配與重置 =================
def choose_team_for_student(age_group: str):
    teams = st.session_state.teams
    max_size = int(st.session_state.team_size)

    if not teams or all(len(t["members"]) >= max_size for t in teams):
        return None

    # 若不平衡年齡，直接找人最少的
    if not st.session_state.balance_age:
        candidates = [
            (idx, len(t["members"]))
            for idx, t in enumerate(teams)
            if len(t["members"]) < max_size
        ]
        if not candidates:
            return None
        min_total = min(c[1] for c in candidates)
        candidates = [c for c in candidates if c[1] == min_total]
        return random.choice(candidates)[0]

    # 若需平衡年齡
    candidates = []
    for idx, team in enumerate(teams):
        if len(team["members"]) >= max_size:
            continue
        same_age = sum(1 for m in team["members"] if m["age_group"] == age_group)
        total = len(team["members"])
        candidates.append((idx, same_age, total))

    if not candidates:
        return None

    # 優先選「該年齡層人數最少」的隊伍
    min_age = min(c[1] for c in candidates)
    candidates = [c for c in candidates if c[1] == min_age]
    # 如果平手，選「總人數最少」的
    min_total = min(c[2] for c in candidates)
    candidates = [c for c in candidates if c[2] == min_total]
    return random.choice(candidates)[0]


def update_student_team_summary():
    teams = st.session_state.teams
    try:
        max_size = int(st.session_state.team_size)
    except ValueError:
        max_size = 0

    lines = []
    for t in teams:
        lines.append(f"{t['name']}：{len(t['members'])} / {max_size} 人")
    return "\n".join(lines)


def build_log_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["序號", "姓名", "年齡級距", "隊伍名稱"])
    for idx, stu in enumerate(st.session_state.students, start=1):
        writer.writerow([idx, stu["name"], stu["age_group"], stu["team"]])
    return buf.getvalue().encode("utf-8-sig")


def reset_all(clear_students: bool = True):
    """依照目前設定重建隊伍，並徹底清除 UI 狀態。"""
    if st.session_state.team_count <= 0 or st.session_state.team_size <= 0:
        st.warning("隊伍數量與每隊上限人數必須大於 0。")
        return

    ensure_team_names_length()
    
    # 重建隊伍結構
    st.session_state.teams = [
        {"name": n, "members": []} for n in st.session_state.team_names
    ]
    
    # 是否清空學生資料
    if clear_students:
        st.session_state.students = []
        st.session_state.last_assignment = None

    # 【重要修正】刪除所有隊名輸入框的暫存 Key，確保 UI 更新為預設值
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith("teamname_")]
    for k in keys_to_remove:
        del st.session_state[k]

    save_state_to_file()
    # 【重要修正】強制刷新頁面
    st.rerun()


def add_student(name: str, age_group: str, team_index: int):
    """共用的加入隊伍函式。"""
    team = st.session_state.teams[team_index]
    max_size = int(st.session_state.team_size)
    if len(team["members"]) >= max_size:
        st.warning(f"{team['name']} 已經滿員。")
        return False
    
    member = {"name": name, "age_group": age_group}
    team["members"].append(member)
    st.session_state.students.append(
        {"name": name, "age_group": age_group, "team": team["name"]}
    )
    st.session_state.last_assignment = {"name": name, "team": team["name"]}
    save_state_to_file()
    return True


# ================= 主程式開始 =================
init_state()

st.title(f"🎄 {st.session_state.theme}")

tab_student, tab_teacher = st.tabs(["🎓 學生畫面", "🧑‍🏫 老師後台"])

# ================== 學生畫面 ==================
with tab_student:
    st.subheader("學生畫面")
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.markdown("#### 輸入資訊")
        # 【重要修正】加上 key="student_name_input"，防止因 label 改變導致輸入框被清空
        name_label = "姓名（必填）" if st.session_state.require_name else "姓名（可留白）"
        name = st.text_input(name_label, key="student_name_input")
        
        age = st.selectbox("年齡級距", AGE_GROUPS, key="student_age")

        if st.button("🎩 分類！", key="sort_button"):
            raw_name = name.strip()
            if st.session_state.require_name and not raw_name:
                st.warning("老師有設定需要填姓名喔～請先輸入姓名再按分類。")
            else:
                idx = choose_team_for_student(age)
                if idx is None:
                    st.error("所有隊伍都已滿，無法再分配。")
                else:
                    display_name = raw_name if raw_name else "這位勇者"

                    # 小轉盤動畫
                    placeholder = st.empty()
                    team_names = [t["name"] for t in st.session_state.teams]
                    
                    # 避免沒有隊伍時轉盤報錯
                    if not team_names:
                        st.error("目前沒有隊伍可供分配，請老師先去後台設定。")
                    else:
                        spins = 15
                        for k in range(spins):
                            showing = team_names[k % len(team_names)]
                            placeholder.markdown(
                                f"### {display_name}，分類中……\n\n🎯 {showing}"
                            )
                            time.sleep(0.08)

                        # 真正加入隊伍 + 大字報
                        if add_student(display_name, age, idx):
                            team_name = st.session_state.teams[idx]["name"]
                            placeholder.markdown(
                                f"""
                                <div style="
                                    text-align: center;
                                    padding: 40px 20px;
                                    border-radius: 32px;
                                    border: 6px solid #FACC15;
                                    background-color: #020617;
                                    color: #F9FAFB;
                                    margin-top: 24px;
                                ">
                                    <div style="font-size: 3.5rem; font-weight: 800; margin-bottom: 24px;">
                                        {display_name}
                                    </div>
                                    <div style="font-size: 2.4rem; margin-bottom: 16px;">
                                        你被分到……
                                    </div>
                                    <div style="font-size: 3.8rem; font-weight: 900; color: #FBBF24;">
                                        {team_name}
                                    </div>
                                    <div style="font-size: 2.4rem; margin-top: 16px;">
                                        🎉
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            # 稍作停頓後刷新，確保大字報出來，同時資料也存進去
                            # 但為了保留大字報給學生看，這裡選擇不自動 rerun，讓學生自己看爽再說。
                            # 老師後台的資料會在按按鈕或切換時更新。

    with col_right:
        st.markdown("#### 分類結果顯示區")
        if st.session_state.last_assignment:
            last = st.session_state.last_assignment
            st.markdown(
                f"## 最近一次分配\n\n**{last['name']}** 被分到 👉 **{last['team']}**"
            )
        else:
            st.info("目前尚未有任何分配。")

        st.markdown("#### 各隊目前人數")
        summary_text = update_student_team_summary()
        st.text(summary_text if summary_text else "尚未建立隊伍。")

# ================== 老師後台 ==================
with tab_teacher:
    st.subheader("老師後台設定與紀錄")

    st.markdown("### 系統設定")
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        st.session_state.theme = st.text_input(
            "主題名稱", value=st.session_state.theme
        )
    with c2:
        st.session_state.team_count = st.number_input(
            "隊伍數量",
            min_value=1,
            max_value=20,
            value=int(st.session_state.team_count),
            step=1,
        )
    with c3:
        st.session_state.team_size = st.number_input(
            "每隊上限人數",
            min_value=1,
            max_value=500,
            value=int(st.session_state.team_size),
            step=1,
        )

    # 隊伍名稱：每隊一個欄位
    st.markdown("#### 隊伍名稱設定")
    ensure_team_names_length()
    new_names = []
    
    # 動態產生輸入框
    for i in range(st.session_state.team_count):
        default_val = (
            st.session_state.team_names[i]
            if i < len(st.session_state.team_names)
            else f"第{i+1}隊"
        )
        # 用 key 來綁定，以便在 reset_all 時可以清除它
        val = st.text_input(f"第 {i+1} 隊名稱", value=default_val, key=f"teamname_{i}")
        new_names.append(val.strip() or f"第{i+1}隊")
    
    st.session_state.team_names = new_names

    st.session_state.balance_age = st.checkbox(
        "平均分散各年齡層到各隊（建議勾選）",
        value=st.session_state.balance_age,
    )
    st.session_state.require_name = st.checkbox(
        "分組時必須輸入姓名", value=st.session_state.require_name
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("套用設定並重設隊伍（清空分配）"):
            reset_all(clear_students=True)
            # reset_all 裡面已經有 rerun，這行之後的程式碼通常不會執行到
            
    with col_btn2:
        if st.session_state.students:
            csv_data = build_log_csv()
            st.download_button(
                label="下載分組 Log（CSV）",
                data=csv_data,
                file_name="sorting_log.csv",
                mime="text/csv",
            )
        else:
            st.info("目前沒有可下載的 Log（尚未有任何分配）。")

    st.markdown("---")

    # 手動加入指定隊伍
    st.markdown("### 手動調整分組")
    if not st.session_state.teams:
        st.info("尚未建立隊伍。")
    else:
        col_m1, col_m2, col_m3, col_m4 = st.columns([2, 2, 2, 2])
        with col_m1:
            manual_name = st.text_input("姓名（手動加入）", key="manual_name")
        with col_m2:
            manual_age = st.selectbox(
                "年齡級距（手動）", AGE_GROUPS, key="manual_age"
            )
        with col_m3:
            team_options = [t["name"] for t in st.session_state.teams]
            manual_team_name = st.selectbox(
                "指定隊伍", team_options, key="manual_team_name"
            )
        with col_m4:
            if st.button("加入指定隊伍", key="manual_add_button"):
                mn = manual_name.strip() or "這位勇者"
                try:
                    idx = team_options.index(manual_team_name)
                    if add_student(mn, manual_age, idx):
                        st.success(f"{mn} 已手動加入 {manual_team_name}。")
                        time.sleep(1) # 給使用者一點時間看成功訊息
                        st.rerun()    # 刷新頁面更新列表
                except ValueError:
                    st.error("隊伍名稱不匹配，請確認設定。")

    st.markdown("---")

    # 紀錄＆隊伍狀態
    col_log, col_team = st.columns(2)
    with col_log:
        st.markdown("### 已分類學生紀錄")
        if not st.session_state.students:
            st.info("尚無已分類學生。")
        else:
            lines = [
                f"{idx}. {stu['name']}（{stu['age_group']}）→ {stu['team']}"
                for idx, stu in enumerate(st.session_state.students, start=1)
            ]
            st.text("\n".join(lines))

    with col_team:
        st.markdown("### 隊伍詳細狀態")
        teams = st.session_state.teams
        if not teams:
            st.info("尚未建立隊伍。")
        else:
            try:
                max_size = int(st.session_state.team_size)
            except ValueError:
                max_size = 0

            st.markdown(
                f"**總人數：** {len(st.session_state.students)}　｜　"
                f"**隊伍數：** {len(teams)}　｜　"
                f"**每隊上限：** {max_size}"
            )
            st.markdown("---")

            for t in teams:
                st.markdown(
                    f"#### {t['name']}（{len(t['members'])} / {max_size} 人）"
                )
                if not t["members"]:
                    st.write("（目前尚無成員）")
                else:
                    ordered = sorted(
                        t["members"],
                        key=lambda m: AGE_GROUPS.index(m["age_group"])
                        if m["age_group"] in AGE_GROUPS
                        else 99,
                    )
                    for m in ordered:
                        st.write(f"- {m['name']}（{m['age_group']}）")
                st.markdown("---")
