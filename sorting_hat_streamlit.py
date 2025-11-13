# -*- coding: utf-8 -*-
import streamlit as st
import random
import time
import io
import csv

AGE_GROUPS = ["低年級", "中年級", "高年級", "國中以上"]

st.set_page_config(page_title="聖誕節分類帽系統", layout="wide")


# ========= 初始化狀態 =========
def init_state():
    if "initialized" in st.session_state:
        return

    st.session_state.initialized = True
    st.session_state.theme = "聖誕節分類帽分組系統"
    st.session_state.team_count = 3
    st.session_state.team_size = 100
    st.session_state.team_names_string = "麋鹿隊, 雪人隊, 聖誕樹隊"
    st.session_state.balance_age = True

    st.session_state.students = []  # list of {name, age_group, team}
    st.session_state.teams = []     # list of {name, members: [{name, age_group}]}
    st.session_state.last_assignment = None

    # 建立預設隊伍
    reset_all(clear_students=False)


def get_team_names(team_count: int, team_names_string: str):
    raw = (team_names_string or "").strip()
    names = []

    if raw:
        parts = raw.split(",")
        for p in parts:
            name = p.strip()
            if name:
                names.append(name)

    if len(names) < team_count:
        for i in range(len(names), team_count):
            names.append(f"第{i+1}隊")
    elif len(names) > team_count:
        names = names[:team_count]

    if not names:
        names = [f"第{i+1}隊" for i in range(team_count)]

    return names


def reset_all(clear_students: bool = True):
    """重新建立隊伍，必要時一併清空學生紀錄。"""
    team_count = int(st.session_state.team_count)
    team_size = int(st.session_state.team_size)

    if team_count <= 0 or team_size <= 0:
        st.warning("隊伍數量與每隊上限人數必須大於 0。")
        return

    names = get_team_names(team_count, st.session_state.team_names_string)

    st.session_state.teams = [
        {"name": names[i], "members": []}
        for i in range(team_count)
    ]

    if clear_students:
        st.session_state.students = []
        st.session_state.last_assignment = None


def choose_team_for_student(age_group: str):
    """根據設定挑選適合的隊伍 index。"""
    teams = st.session_state.teams
    max_size = int(st.session_state.team_size)

    if not teams:
        return None

    # 所有隊伍都滿了
    if all(len(t["members"]) >= max_size for t in teams):
        return None

    # 如果不考慮年齡平衡，只看總人數
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

    # 有啟用年齡平衡
    candidates = []
    for idx, team in enumerate(teams):
        if len(team["members"]) >= max_size:
            continue
        same_age = sum(1 for m in team["members"] if m["age_group"] == age_group)
        total = len(team["members"])
        candidates.append((idx, same_age, total))

    if not candidates:
        return None

    # 年齡層人數最少優先
    min_age = min(c[1] for c in candidates)
    candidates = [c for c in candidates if c[1] == min_age]

    # 總人數最少優先
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
        name = st.text_input("姓名", key="student_name")
        age = st.selectbox("年齡級距", AGE_GROUPS, key="student_age")

        if st.button("🎩 分類！", key="sort_button"):
            if not name.strip():
                st.warning("請先輸入姓名。")
            else:
                idx = choose_team_for_student(age)
                if idx is None:
                    st.error("所有隊伍都已滿，無法再分配。")
                else:
                    # 轉盤動畫
                    placeholder = st.empty()
                    team_names = [t["name"] for t in st.session_state.teams]

                    spins = 18
                    for k in range(spins):
                        showing = team_names[k % len(team_names)]
                        placeholder.markdown(
                            f"### {name}，分類中……\n\n🎯 【{showing}】"
                        )
                        time.sleep(0.08)

                    # 真正分配
                    team = st.session_state.teams[idx]
                    member = {"name": name.strip(), "age_group": age}
                    team["members"].append(member)
                    st.session_state.students.append(
                        {"name": name.strip(), "age_group": age, "team": team["name"]}
                    )
                    st.session_state.last_assignment = {
                        "name": name.strip(),
                        "team": team["name"],
                    }

                    placeholder.markdown(
                        f"## {name}，你被分到：🎉\n\n# 【{team['name']}】"
                    )

                    # 清空姓名方便下一位
                    st.session_state.student_name = ""

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

    st.session_state.team_names_string = st.text_input(
        "隊伍名稱（以半形逗號分隔，可留白）",
        value=st.session_state.team_names_string,
        help="例如：麋鹿隊, 雪人隊, 聖誕樹隊",
    )

    st.session_state.balance_age = st.checkbox(
        "平均分散各年齡層到各隊（建議勾選）",
        value=st.session_state.balance_age,
    )

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if st.button("套用設定並重設隊伍（清空分配）"):
            reset_all(clear_students=True)
            st.success("已依照目前設定重設隊伍並清空分配紀錄。")

    with col_btn2:
        # 匯出 Log
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
                    # 依年齡排序顯示
                    ordered = sorted(
                        t["members"],
                        key=lambda m: AGE_GROUPS.index(m["age_group"])
                        if m["age_group"] in AGE_GROUPS
                        else 99,
                    )
                    for m in ordered:
                        st.write(f"- {m['name']}（{m['age_group']}）")
                st.markdown("---")
