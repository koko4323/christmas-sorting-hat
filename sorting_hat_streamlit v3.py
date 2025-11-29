# -*- coding: utf-8 -*-
import streamlit as st
import random
import time
import io
import csv
import json
import os

AGE_GROUPS = ["低年級", "中年級", "高年級", "國中以上"]
STATE_FILE = "sorting_hat_state.json"

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

# ========= 狀態持久化（存到 JSON 檔） =========

def save_state():
    """把目前狀態寫進 JSON 檔，避免重整後消失。"""
    data = {
        "theme": st.session_state.theme,
        "team_count": st.session_state.team_count,
        "team_size": st.session_state.team_size,
        "require_name": st.session_state.require_name,
        "balance_age": st.session_state.balance_age,
        "team_names": get_current_team_names(),
        "students": st.session_state.students,
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # 檔案寫不出去就先忽略，不影響當前遊戲
        pass


def load_state():
    """從 JSON 檔讀取狀態，回傳 dict 或 None。"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def rebuild_teams_from_students(team_names):
    """依照 team_names + students 重建各隊成員。"""
    team_count = len(team_names)
    st.session_state.teams = [{"name": team_names[i], "members": []} for i in range(team_count)]
    name_to_team = {t["name"]: t for t in st.session_state.teams}

    for stu in st.session_state.students:
        tname = stu.get("team")
        team = name_to_team.get(tname)
        if team is None:
            continue
        team["members"].append(
            {"name": stu["name"], "age_group": stu["age_group"]}
        )


def ensure_team_name_keys():
    """確保每一隊都有對應的 team_name_i widget key。"""
    for i in range(st.session_state.team_count):
        key = f"team_name_{i}"
        if key not in st.session_state:
            # 給一個預設：如果有舊名單就用舊的，否則用「第X隊」
            if "team_names" in st.session_state and i < len(st.session_state.team_names):
                st.session_state[key] = st.session_state.team_names[i]
            else:
                st.session_state[key] = f"第 {i+1} 隊"


def get_current_team_names():
    """從各個 team_name_i widget 把目前隊名抓出來。"""
    names = []
    for i in range(st.session_state.team_count):
        key = f"team_name_{i}"
        val = st.session_state.get(key, f"第 {i+1} 隊")
        name = val.strip() or f"第 {i+1} 隊"
        names.append(name)
    # 也同步存一份在 session_state 方便外面用
    st.session_state.team_names = names
    return names

# ========= 初始化狀態 =========

def init_state():
    if "initialized" in st.session_state:
        return

    # 預設值
    st.session_state.theme = "聖誕節分類帽分組系統"
    st.session_state.team_count = 3
    st.session_state.team_size = 100
    st.session_state.require_name = True
    st.session_state.balance_age = True
    st.session_state.students = []
    st.session_state.teams = []
    st.session_state.last_assignment = None
    st.session_state.team_names = ["麋鹿隊", "雪人隊", "聖誕樹隊"]

    # 先嘗試從檔案載入
    data = load_state()
    if data:
        st.session_state.theme = data.get("theme", st.session_state.theme)
        st.session_state.team_count = int(data.get("team_count", st.session_state.team_count))
        st.session_state.team_size = int(data.get("team_size", st.session_state.team_size))
        st.session_state.require_name = bool(data.get("require_name", st.session_state.require_name))
        st.session_state.balance_age = bool(data.get("balance_age", st.session_state.balance_age))
        st.session_state.students = data.get("students", [])
        st.session_state.team_names = data.get("team_names", st.session_state.team_names)

        # 防止隊伍數量與隊名長度不一致
        if st.session_state.team_count < len(st.session_state.team_names):
            st.session_state.team_names = st.session_state.team_names[: st.session_state.team_count]
        elif st.session_state.team_count > len(st.session_state.team_names):
            for i in range(len(st.session_state.team_names), st.session_state.team_count):
                st.session_state.team_names.append(f"第 {i+1} 隊")

        # 重建隊伍
        rebuild_teams_from_students(st.session_state.team_names)
    else:
        # 沒有舊檔案就用預設隊伍並先存一份
        rebuild_teams_from_students(st.session_state.team_names)
        save_state()

    # 把隊名塞進 widget key
    for i, name in enumerate(st.session_state.team_names):
        st.session_state[f"team_name_{i}"] = name

    st.session_state.initialized = True

# ========= 分配相關邏輯 =========

def choose_team_for_student(age_group: str):
    """根據設定挑選適合的隊伍 index。"""
    teams = st.session_state.teams
    max_size = int(st.session_state.team_size)

    if not teams:
        return None

    if all(len(t["members"]) >= max_size for t in teams):
        return None

    # 不平均年齡時：只看總人數
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

    # 有平均年齡時：先比該年齡層，再比總人數
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


def reset_teams(clear_students: bool = True):
    """依目前設定 + 隊名重建隊伍，可選擇是否清空學生。"""
    team_count = int(st.session_state.team_count)
    if team_count <= 0:
        st.warning("隊伍數量必須大於 0。")
        return
    ensure_team_name_keys()
    names = get_current_team_names()

    st.session_state.teams = [{"name": names[i], "members": []} for i in range(team_count)]
    if clear_students:
        st.session_state.students = []
        st.session_state.last_assignment = None

    save_state()

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

                    # 放大顯示結果（提高對比＋顯示隊名）
                    placeholder.markdown(
                        f"""
                        <div style="
                            text-align: center;
                            padding: 40px 20px;
                            border-radius: 20px;
                            border: 4px solid #FFD700;
                            background-color: #202437;
                            color: #FFFFFF;
                            margin-top: 20px;
                        ">
                            <h1 style="font-size: 3.2rem; margin-bottom: 20px;">{display_name}</h1>
                            <h2 style="font-size: 2.4rem; margin-bottom: 10px;">你被分到…… 🎉</h2>
                            <h1 style="font-size: 4rem; color: #FFE066;"></h1>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    save_state()

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

    # 確保隊名欄位存在
    ensure_team_name_keys()

    st.markdown("#### 隊伍名稱設定（一隊一欄位）")
    for i in range(st.session_state.team_count):
        key = f"team_name_{i}"
        st.text_input(
            f"第 {i+1} 隊名稱",
            key=key,
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
            reset_teams(clear_students=True)
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

    # ===== 手動分配到特定隊伍 =====
    st.markdown("### 手動分配到指定隊伍")

    if not st.session_state.teams:
        st.info("目前尚未建立任何隊伍。")
    else:
        col_manual1, col_manual2 = st.columns(2)

        with col_manual1:
            manual_name = st.text_input("學生姓名（可留白）", key="manual_name")
            manual_age = st.selectbox("年齡級距（手動分配）", AGE_GROUPS, key="manual_age")

        with col_manual2:
            team_options = [t["name"] for t in st.session_state.teams]
            manual_team = st.selectbox("指定隊伍", team_options, key="manual_team")

            if st.button("加入指定隊伍", key="manual_assign_btn"):
                raw_name = manual_name.strip()
                if st.session_state.require_name and not raw_name:
                    st.warning("目前設定為必填姓名，請輸入學生姓名。")
                else:
                    display_name = raw_name if raw_name else "這位勇者"

                    max_size = int(st.session_state.team_size)
                    target = None
                    for t in st.session_state.teams:
                        if t["name"] == manual_team:
                            target = t
                            break

                    if target is None:
                        st.error("找不到指定的隊伍。")
                    elif len(target["members"]) >= max_size:
                        st.warning("這個隊伍已達上限人數，請選擇其他隊伍或調整上限。")
                    else:
                        target["members"].append(
                            {"name": display_name, "age_group": manual_age}
                        )
                        st.session_state.students.append(
                            {
                                "name": display_name,
                                "age_group": manual_age,
                                "team": manual_team,
                            }
                        )
                        st.session_state.last_assignment = {
                            "name": display_name,
                            "team": manual_team,
                        }
                        save_state()
                        st.success(f"{display_name} 已加入 ")

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
