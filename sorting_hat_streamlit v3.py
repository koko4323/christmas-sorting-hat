# -*- coding: utf-8 -*-
import streamlit as st
import random
import time
import io
import csv
import json
import os

AGE_GROUPS = ["低年級", "中年級", "高年級", "國中以上"]
STATE_FILE = "sorting_state.json"

st.set_page_config(page_title="聖誕節分類帽系統", layout="wide")

# ---- 放大按鈕（包含分類鍵）----
st.markdown(
    """
    <style>
    div.stButton > button {
        font-size: 1.4rem;
        padding: 0.8rem 2.5rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ========= 狀態持久化：讀寫 JSON =========
def save_state():
    """把目前 session_state 存成 JSON，避免重整遺失。"""
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
        st.warning(f"儲存狀態失敗：{e}")


def load_state():
    """從 JSON 載入狀態，如果沒有就回傳 None。"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None


# ========= 初始化狀態 =========
def init_state():
    if "initialized" in st.session_state:
        return

    st.session_state.initialized = True

    # 預設值
    st.session_state.theme = "聖誕節分類帽分組系統"
    st.session_state.team_count = 3
    st.session_state.team_size = 100
    st.session_state.team_names = ["麋鹿隊", "雪人隊", "聖誕樹隊"]
    st.session_state.balance_age = True
    st.session_state.require_name = True

    st.session_state.students = []  # list[{name, age_group, team}]
    st.session_state.teams = []     # list[{name, members}]
    st.session_state.last_assignment = None

    # 先建立預設隊伍
    reset_teams(from_load=False, clear_students=True)

    # 嘗試從 JSON 載入舊狀態
    data = load_state()
    if data:
        st.session_state.theme = data.get("theme", st.session_state.theme)
        st.session_state.team_count = data.get("team_count", st.session_state.team_count)
        st.session_state.team_size = data.get("team_size", st.session_state.team_size)
        st.session_state.team_names = data.get("team_names", st.session_state.team_names)
        st.session_state.balance_age = data.get("balance_age", st.session_state.balance_age)
        st.session_state.require_name = data.get("require_name", st.session_state.require_name)
        st.session_state.students = data.get("students", [])
        st.session_state.teams = data.get("teams", st.session_state.teams)
        # last_assignment 不存檔也沒關係，只會影響右側那一小塊顯示


def ensure_team_names_length():
    """依 team_count 補齊 / 截斷 team_names。"""
    names = st.session_state.team_names
    # 補
    while len(names) < st.session_state.team_count:
        names.append(f"第{len(names)+1}隊")
    # 截斷
    if len(names) > st.session_state.team_count:
        names = names[: st.session_state.team_count]
    st.session_state.team_names = names
    return names


def reset_teams(from_load: bool = False, clear_students: bool = False):
    """依目前設定重建隊伍結構。"""
    team_count = int(st.session_state.team_count)
    team_size = int(st.session_state.team_size)

    if team_count <= 0 or team_size <= 0:
        st.warning("隊伍數量與每隊上限人數必須大於 0。")
        return

    names = ensure_team_names_length()

    st.session_state.teams = [
        {"name": names[i], "members": []}
        for i in range(team_count)
    ]

    if clear_students:
        st.session_state.students = []
        st.session_state.last_assignment = None

    if not from_load:
        save_state()


def choose_team_for_student(age_group: str):
    """自動分配隊伍 index。"""
    teams = st.session_state.teams
    max_size = int(st.session_state.team_size)

    if not teams:
        return None

    if all(len(t["members"]) >= max_size for t in teams):
        return None

    # 不平衡，只看總人數
    if not st.session_state.balance_age:
        candidates = []
        for idx, team in enumerate(teams):
            if len(team["members"]) >= max_size:
                continue
            total = len(team["members"])
            candidates.append((idx, total))
        if not candidates:
            return None
        min_total = min(c[1] for c in candidates)
        candidates = [c for c in candidates if c[1] == min_total]
        return random.choice(candidates)[0]

    # 有平衡：優先同年齡層最少、再看總人數
    candidates = []
    for idx, team in enumerate(teams):
        if len(team["members"]) >= max_size:
            continue
        same_age = sum(1 for m in team["members"] if m["age_group"] == age_group)
        total = len(team["members"])
        candidates.append((idx, same_age, total))

    if not candidates:
        return None

    min_age = min(c[1] for c in candidates)
    candidates = [c for c in candidates if c[1] == min_age]

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


# ========= 主程式開始 =========
init_state()

st.title("🎄 聖誕節分類帽系統（Streamlit 版）")

tab_student, tab_teacher = st.tabs(["🎓 學生畫面", "🧑‍🏫 老師後台"])

# ================== 學生畫面 ==================
with tab_student:
    st.subheader("學生畫面")

    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.markdown("#### 輸入資訊")
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

                    placeholder = st.empty()
                    team_names = [t["name"] for t in st.session_state.teams]

                    spins = 18
                    for k in range(spins):
                        showing = team_names[k % len(team_names)]
                        placeholder.markdown(
                            f"""
                            <div style="
                                text-align: center;
                                padding: 40px 20px;
                                border-radius: 20px;
                                border: 4px solid #FACC15;
                                background-color: #111827;
                                margin-top: 20px;
                                color: #F9FAFB;
                            ">
                                <h2 style="font-size: 1.8rem; margin-bottom: 10px;">
                                    {display_name}，分類中……
                                </h2>
                                <h1 style="font-size: 3.2rem; margin: 10px 0;">
                                    🎯 
                                </h1>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        time.sleep(0.08)

                    team = st.session_state.teams[idx]
                    member = {"name": display_name, "age_group": age}
                    team["members"].append(member)
                    st.session_state.students.append(
                        {"name": display_name, "age_group": age, "team": team["name"]}
                    )
                    st.session_state.last_assignment = {
                        "name": display_name,
                        "team": team["name"],
                    }

                    # ✅ 最後結果大字報（這裡一定會顯示隊名）
                    placeholder.markdown(
                        f"""
                        <div style="
                            text-align: center;
                            padding: 50px 20px;
                            border-radius: 24px;
                            border: 6px solid #FACC15;
                            background-color: #020617;
                            margin-top: 20px;
                            color: #F9FAFB;
                        ">
                            <h1 style="font-size: 3.5rem; margin-bottom: 24px; font-weight: 800;">
                                {display_name}
                            </h1>
                            <h2 style="font-size: 2.4rem; margin-bottom: 16px;">
                                你被分到……
                            </h2>
                            <h1 style="font-size: 4.2rem; color: #F97316; font-weight: 900;">
                                
                            </h1>
                            <div style="font-size: 2.5rem; margin-top: 16px;">🎉🎄</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # 存檔（避免重整遺失）
                    save_state()

    with col_right:
        st.markdown("#### 最近一次分配")
        if st.session_state.last_assignment:
            last = st.session_state.last_assignment
            st.markdown(
                f"**{last['name']}** 被分到 👉 **{last['team']}**"
            )
        else:
            st.info("目前尚未有任何分配。")

        st.markdown("#### 各隊目前人數")
        summary_text = update_student_team_summary()
        st.text(summary_text if summary_text else "尚未建立隊伍。")


# ================== 老師後台 ==================
with tab_teacher:
    st.subheader("老師後台設定與紀錄")

    # --- 上方設定 ---
    st.markdown("### 系統設定")

    c1, c2, c3 = st.columns([2, 2, 2])

    with c1:
        st.session_state.theme = st.text_input(
            "主題名稱",
            value=st.session_state.theme,
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

    # ✅ 一隊一欄：動態隊名輸入
    st.markdown("#### 隊伍名稱設定")
    names = ensure_team_names_length()
    new_names = []
    for i in range(st.session_state.team_count):
        n = st.text_input(
            f"第 {i+1} 隊名稱",
            value=names[i],
            key=f"team_name_input_{i}",
        )
        new_names.append(n.strip() or f"第{i+1}隊")
    st.session_state.team_names = new_names

    st.session_state.balance_age = st.checkbox(
        "平均分散各年齡層到各隊（建議勾選）",
        value=st.session_state.balance_age,
    )

    st.session_state.require_name = st.checkbox(
        "分組時必須輸入姓名",
        value=st.session_state.require_name,
        help="取消勾選後，學生可以不記名分組。",
    )

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if st.button("套用設定並重設隊伍（清空分配）"):
            reset_teams(from_load=False, clear_students=True)
            save_state()
            st.success("已依照目前設定重設隊伍並清空分配紀錄。")

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

    # --- 手動分配區塊（老師強制塞人進某隊） ---
    st.markdown("### 手動加入指定隊伍")
    col_m1, col_m2, col_m3 = st.columns([2, 1.5, 1])

    with col_m1:
        manual_name = st.text_input("學生姓名（可空白當匿名）", key="manual_name")
    with col_m2:
        manual_age = st.selectbox(
            "年齡級距（手動）", AGE_GROUPS, key="manual_age"
        )
    with col_m3:
        team_options = [t["name"] for t in st.session_state.teams]
        manual_team_name = st.selectbox(
            "指定隊伍", team_options if team_options else ["尚未建立隊伍"], key="manual_team"
        )

    if st.button("➡ 加入指定隊伍", key="manual_add_button"):
        if not st.session_state.teams:
            st.warning("目前尚未建立任何隊伍。")
        else:
            # 找到指定隊伍
            target = None
            for t in st.session_state.teams:
                if t["name"] == manual_team_name:
                    target = t
                    break
            if target is None:
                st.error("找不到指定隊伍。")
            else:
                # 檢查上限
                if len(target["members"]) >= st.session_state.team_size:
                    st.warning(f"{manual_team_name} 已達上限，無法再加入。")
                else:
                    display_name = manual_name.strip() or "這位勇者"
                    target["members"].append(
                        {"name": display_name, "age_group": manual_age}
                    )
                    st.session_state.students.append(
                        {
                            "name": display_name,
                            "age_group": manual_age,
                            "team": manual_team_name,
                        }
                    )
                    st.session_state.last_assignment = {
                        "name": display_name,
                        "team": manual_team_name,
                    }
                    save_state()
                    st.success(f"已將「{display_name}」加入。")

    st.markdown("---")

    # --- 下方紀錄與隊伍狀態 ---
    col_log, col_team = st.columns(2)

    with col_log:
        st.markdown("### 已分類學生紀錄")
        if not st.session_state.students:
            st.info("尚無已分類學生。")
        else:
            lines = []
            for idx, stu in enumerate(st.session_state.students, start=1):
                lines.append(
                    f"{idx}. {stu['name']}（{stu['age_group']}）→ {stu['team']}"
                )
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
                st.markdown(f"#### {t['name']}（{len(t['members'])} / {max_size} 人）")
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
