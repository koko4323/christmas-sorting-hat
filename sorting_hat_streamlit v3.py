# -*- coding: utf-8 -*-
import streamlit as st
import random
import time
import io
import csv
import json
import os

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

STATE_FILE = "sorting_hat_state.json"

def save_state_to_file():
    """將目前狀態寫入本地 JSON 檔，避免重整後遺失。"""
    try:
        data = {
            "theme": st.session_state.get("theme"),
            "team_count": st.session_state.get("team_count"),
            "team_size": st.session_state.get("team_size"),
            "team_names": st.session_state.get("team_names", []),
            "balance_age": st.session_state.get("balance_age", True),
            "require_name": st.session_state.get("require_name", True),
            "students": st.session_state.get("students", []),
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # 在雲端環境有可能寫入失敗，但不影響主要功能
        st.warning(f"儲存狀態時發生問題：{e}")

def load_state_from_file():
    """從本地 JSON 檔載入狀態（如果存在）。"""
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None

def rebuild_teams_from_students():
    """根據 team_names 與 students 重新建立 teams 結構。"""
    team_names = st.session_state.get("team_names", [])
    team_count = st.session_state.get("team_count", len(team_names) or 3)
    if not team_names or len(team_names) < team_count:
        # 補齊隊名
        team_names = [
            team_names[i] if i < len(team_names) and team_names[i]
            else f"第{i+1}隊"
            for i in range(team_count)
        ]
        st.session_state.team_names = team_names
    teams = [{"name": name, "members": []} for name in team_names]

    name_to_team = {t["name"]: t for t in teams}
    for stu in st.session_state.students:
        team_name = stu.get("team")
        if team_name in name_to_team:
            name_to_team[team_name]["members"].append(
                {"name": stu.get("name", "這位勇者"), "age_group": stu.get("age_group", AGE_GROUPS[0])}
            )
    st.session_state.teams = teams

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
    st.session_state.students = []
    st.session_state.teams = []
    st.session_state.last_assignment = None

    # 讀取已存狀態（如果有）
    data = load_state_from_file()
    if data:
        st.session_state.theme = data.get("theme", st.session_state.theme)
        st.session_state.team_count = data.get("team_count", st.session_state.team_count)
        st.session_state.team_size = data.get("team_size", st.session_state.team_size)
        st.session_state.team_names = data.get("team_names", st.session_state.team_names)
        st.session_state.balance_age = data.get("balance_age", st.session_state.balance_age)
        st.session_state.require_name = data.get("require_name", st.session_state.require_name)
        st.session_state.students = data.get("students", st.session_state.students)

    # 依目前設定重建隊伍
    rebuild_teams_from_students()

def get_team_names_from_inputs():
    """從老師後台的每隊輸入欄位取得隊名。"""
    names = []
    for i in range(st.session_state.team_count):
        key = f"team_name_{i}"
        val = st.session_state.get(key, "").strip() if isinstance(st.session_state.get(key), str) else ""
        if not val:
            val = f"第{i+1}隊"
        names.append(val)
    st.session_state.team_names = names
    return names

def reset_all(clear_students: bool = True):
    """重新建立隊伍，必要時一併清空學生紀錄。"""
    team_count = int(st.session_state.team_count)
    team_size = int(st.session_state.team_size)

    if team_count <= 0 or team_size <= 0:
        st.warning("隊伍數量與每隊上限人數必須大於 0。")
        return

    # 讀取目前輸入的隊名
    names = get_team_names_from_inputs()

    st.session_state.teams = [
        {"name": names[i], "members": []}
        for i in range(team_count)
    ]

    if clear_students:
        st.session_state.students = []
        st.session_state.last_assignment = None

    save_state_to_file()

def choose_team_for_student(age_group: str):
    """根據設定挑選適合的隊伍 index。"""
    teams = st.session_state.teams
    max_size = int(st.session_state.team_size)

    if not teams:
        return None

    if all(len(t["members"]) >= max_size for t in teams):
        return None

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
        name = st.text_input(name_label)
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
                            f"### {display_name}，分類中……\n\n🎯 "
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

                    placeholder.markdown(
                        f"""
                        <div style="
                            text-align: center;
                            padding: 40px 20px;
                            border-radius: 20px;
                            border: 4px solid #ff4b4b;
                            background-color: #ffecec;
                            margin-top: 20px;
                        ">
                            <h1 style="font-size: 3.2rem; margin-bottom: 20px;">{display_name}</h1>
                            <h2 style="font-size: 2.4rem; margin-bottom: 10px;">你被分到…… 🎉</h2>
                            <h1 style="font-size: 4rem; color: #d60000;"></h1>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    save_state_to_file()

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

    # 依隊伍數顯示多個隊名輸入欄位
    st.markdown("#### 隊伍名稱設定")
    team_name_cols = st.columns(2)
    for i in range(st.session_state.team_count):
        col = team_name_cols[i % 2]
        default_name = (
            st.session_state.team_names[i]
            if i < len(st.session_state.team_names)
            else f"第{i+1}隊"
        )
        col.text_input(
            f"第 {i+1} 隊名稱",
            value=default_name,
            key=f"team_name_{i}",
        )

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
            reset_all(clear_students=True)
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

    # 手動分配區塊
    st.markdown("### 手動分配學生到指定隊伍")
    mcol1, mcol2, mcol3, mcol4 = st.columns([2, 1.5, 1.5, 1])
    with mcol1:
        manual_name = st.text_input("學生姓名（可留白）", key="manual_name")
    with mcol2:
        manual_age = st.selectbox(
            "年齡級距",
            AGE_GROUPS,
            key="manual_age",
        )
    with mcol3:
        team_options = [t["name"] for t in st.session_state.teams] or ["尚未建立隊伍"]
        manual_team = st.selectbox("指定隊伍", team_options, key="manual_team")
    with mcol4:
        if st.button("手動加入", key="manual_assign_button"):
            if not st.session_state.teams:
                st.warning("尚未建立任何隊伍，無法手動分配。")
            else:
                display_name = manual_name.strip() or "這位勇者"
                # 找到隊伍
                target_index = None
                for idx, t in enumerate(st.session_state.teams):
                    if t["name"] == manual_team:
                        target_index = idx
                        break
                if target_index is None:
                    st.error("找不到指定的隊伍。")
                else:
                    team = st.session_state.teams[target_index]
                    member = {"name": display_name, "age_group": manual_age}
                    team["members"].append(member)
                    st.session_state.students.append(
                        {
                            "name": display_name,
                            "age_group": manual_age,
                            "team": team["name"],
                        }
                    )
                    st.session_state.last_assignment = {
                        "name": display_name,
                        "team": team["name"],
                    }
                    save_state_to_file()
                    st.success(f"{display_name} 已被手動加入。")

    st.markdown("---")

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
