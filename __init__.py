import json
import math

from comfy_api.latest import ComfyExtension, io


WEB_DIRECTORY = "./web"
DETAIL_FIELDS = {
    "subject_kind": False, "background_source": False, "action": True,
    "framing": False, "camera_direction": False, "camera": True,
    "lighting": True, "style": False, "soundscape": True, "music": True,
}


def parse_details(value):
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("시간·프롬프트 설정을 읽을 수 없습니다.") from exc
    if not isinstance(data, dict) or set(data) - {"duration", "fields"}:
        raise ValueError("시간·프롬프트 설정 형식이 잘못되었습니다.")
    duration = data.get("duration", 5)
    if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration <= 150:
        raise ValueError("영상 길이는 0초 초과, 150초 이하여야 합니다.")
    fields = data.get("fields", {})
    if not isinstance(fields, dict) or set(fields) - DETAIL_FIELDS.keys():
        raise ValueError("지원하지 않는 추가 프롬프트 항목입니다.")
    for name, entry in fields.items():
        if not isinstance(entry, dict) or set(entry) - {"prompt", "start", "end"}:
            raise ValueError(f"{name}: 추가 프롬프트 형식이 잘못되었습니다.")
        if not isinstance(entry.get("prompt", ""), str):
            raise ValueError(f"{name}: 프롬프트는 문자열이어야 합니다.")
        if "start" in entry or "end" in entry:
            start, end = entry.get("start"), entry.get("end")
            if not DETAIL_FIELDS[name]:
                raise ValueError(f"{name}: 시간 구간을 지원하지 않는 항목입니다.")
            if any(type(t) not in (int, float) or not math.isfinite(t) for t in (start, end)) or not 0 <= start < end <= duration:
                raise ValueError(f"{name}: 0 ≤ 시작 < 종료 ≤ 영상 길이({duration}초)를 지켜주세요.")
    return data, fields


def describe_interval(text, entry, label):
    extra = entry.get("prompt", "").strip()
    if extra:
        text = ("" if text == "N/A" else text + " ") + extra
    if "start" in entry:
        text = text.replace("throughout the shot", "during this interval").replace("throughout the video", "during this interval")
        return f"{label} applies from {entry['start']:.3f} to {entry['end']:.3f} seconds: {text}"
    return text


VISUAL_SOURCES = [f"<Picture {i}>" for i in range(1, 10)] + [f"<Video {i}>" for i in range(1, 4)]
NONE = "사용 안 함"
OPTIONS = {
    "subject_kind": ("주인공 종류", {
        "인물": "the main person", "동물": "the main animal", "제품·사물": "the main object",
    }),
    "action": ("행위·동작", {
        "자연스럽게 유지": "remains in place with subtle, natural movement",
        "카메라 쪽으로 이동": "moves slowly toward the camera, then settles to a stop",
        "왼쪽에서 오른쪽으로 이동": "moves steadily from the left side of the frame to the right",
        "천천히 회전": "turns slowly to reveal a three-quarter view, then holds that orientation",
        "주변 둘러보기": "looks slowly from one side of the environment to the other, then looks forward",
        "미소 짓기": "looks toward the camera and gradually forms a relaxed smile",
        "인물 · 걷기": "starts standing, walks forward for a few relaxed steps, then comes to a gentle stop",
        "인물 · 달리기": "leans forward, runs a short distance with coordinated arm and leg movement, then slows to a stop",
        "인물 · 앉기": "starts standing in front of a chair, bends at the hips and knees, and settles onto the seat",
        "인물 · 일어서기": "starts seated on a chair, leans forward, and rises into a balanced standing position",
        "인물 · 손 흔들기": "raises one hand, waves it gently from side to side in greeting, then lowers it",
        "인물 · 고개 끄덕이기": "gently nods once in acknowledgment, then returns to a relaxed head position",
        "인물 · 인사하며 숙이기": "bows the upper body politely, pauses briefly, then straightens up",
        "인물 · 박수 치기": "brings both hands together for a short round of applause, then lowers them",
        "인물 · 춤추기": "performs a short dance with small rhythmic steps and coordinated arm movements, then finishes in a balanced pose",
        "인물 · 스트레칭": "raises both arms overhead, stretches upward gently, then lowers the arms and relaxes",
        "인물 · 컵으로 마시기": "starts holding a cup, brings it to the lips, takes a small sip, then lowers the cup",
        "인물 · 책 읽기": "starts holding an open book, follows the page with the eyes, turns one page, then resumes reading",
        "인물 · 휴대폰 보기": "starts holding a smartphone, looks down at its screen, makes a brief scrolling gesture, then holds it still",
        "인물 · 물건 집어 들기": "reaches toward a small object on a nearby table, grasps it, and lifts it to chest level for inspection",
        "동물 · 걷기": "walks forward with a natural gait, slows down, and stops in a relaxed stance",
        "동물 · 냄새 맡기": "lowers its head toward the ground, sniffs a small area, then gently raises its head",
        "동물 · 앉기": "starts standing, lowers its hindquarters into a seated position, then rests calmly",
        "동물 · 기지개 켜기": "extends its front legs and lowers its chest in a gentle stretch, then returns to a relaxed stance",
        "제품 · 제자리 전시": "remains stationary on a clean display surface, with its silhouette and visible details held steady",
        "제품 · 360도 회전 전시": "rotates smoothly through one full revolution around its vertical axis on a display turntable, then stops in its original orientation",
        "제품 · 공중 부유": "floats gently above a display surface with a subtle vertical drift, then settles into a steady suspended position",
    }),
    "framing": ("구도", {
        "미디엄 샷": "A medium shot places the subject at the center of the frame",
        "클로즈업": "A close-up fills the frame with the subject's most recognizable details",
        "와이드 샷": "A wide shot places the subject in the middle ground with the environment clearly visible",
        "전신·전체 샷": "A full shot keeps the entire subject visible with space around its silhouette",
    }),
    "camera": ("카메라 움직임", {
        "고정": "The camera stays locked in position throughout the shot",
        "천천히 다가가기": "The camera makes a slow, short dolly move toward the subject",
        "천천히 멀어지기": "The camera pulls back slowly, revealing more of the surroundings",
        "옆으로 따라가기": "The camera tracks smoothly alongside the subject at a steady distance",
        "반원 궤도 이동": "The camera slowly arcs around the subject through a half circle",
    }),
    "lighting": ("조명", {
        "부드러운 자연광": "Soft daylight produces gentle shadows and balanced exposure",
        "골든아워": "Low golden sunlight creates warm highlights and long, soft-edged shadows",
        "스튜디오": "A broad studio key light and soft fill reveal surface detail against controlled shadows",
        "야간 네온": "Colored neon light traces the subject's edges against a dim evening environment",
    }),
    "style": ("영상 스타일", {
        "실사 영화": "The target video has a live-action cinematic look with realistic materials and restrained color grading.",
        "다큐멘터리": "The target video has a natural documentary look with lifelike textures and neutral colors.",
        "제품 광고": "The target video has a polished commercial look with clean surfaces and precise visual detail.",
        "3D 애니메이션": "The target video has a stylized 3D animated look with coherent shapes and softly rendered materials.",
        "2D 애니메이션": "The target video has a 2D animated look with clean outlines and consistent painted shading.",
    }),
    "soundscape": ("환경음", {
        "조용한 실내": "A quiet indoor air tone continues evenly, with faint movement sounds synchronized to visible actions.",
        "자연": "A light breeze and distant birds form a soft outdoor ambience, with nearby motion sounds matching the image.",
        "도시": "Distant traffic and a soft city rumble continue beneath sounds caused by visible movement.",
        "환경음 없음": "No environmental sound effects or ambient noise.",
    }),
    "music": ("배경음악", {
        "없음": "N/A",
        "잔잔한 피아노": "A quiet solo piano plays at a slow tempo with widely spaced notes and a gentle decay at the end.",
        "어쿠스틱": "Soft acoustic guitar plays a relaxed mid-tempo pattern, keeping a steady low volume before fading out.",
        "시네마틱": "Low strings and a restrained piano motif build slowly, then resolve softly at the end.",
        "전자음악": "A light synthesizer pulse and muted percussion keep a steady mid-tempo beat with a brief final fade.",
    }),
    "camera_direction": ("카메라 방향 (시작 시점)", {
        "지정 안 함": "",
        "전면": "At the start, the camera views <Subject 1> directly from the front.",
        "좌측면": "At the start, the camera views <Subject 1> in profile from the subject's left side.",
        "우측면": "At the start, the camera views <Subject 1> in profile from the subject's right side.",
        "후면": "At the start, the camera views <Subject 1> directly from behind.",
        "좌측 전방 사선": "At the start, the camera views <Subject 1> from a front-left three-quarter angle, relative to the subject.",
        "우측 전방 사선": "At the start, the camera views <Subject 1> from a front-right three-quarter angle, relative to the subject.",
        "좌측 후방 사선": "At the start, the camera views <Subject 1> from a rear-left three-quarter angle, relative to the subject.",
        "우측 후방 사선": "At the start, the camera views <Subject 1> from a rear-right three-quarter angle, relative to the subject.",
        "위에서 내려다보기": "At the start, the camera looks down at <Subject 1> from a high angle.",
        "아래에서 올려다보기": "At the start, the camera looks up at <Subject 1> from a low angle.",
        "수직 탑뷰": "At the start, the camera looks vertically down at <Subject 1> from directly overhead.",
    }),
}


class MiniMaxH3RefPromptBuilder(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        inputs = [
            io.Combo.Input("subject_source", display_name="주인공 참조", options=VISUAL_SOURCES,
                tooltip="Reference to Video에 실제 연결한 자료의 태그를 선택하세요. 파일 내용을 분석하지 않습니다."),
            io.Combo.Input("background_source", display_name="배경 참조", options=[NONE] + VISUAL_SOURCES),
            io.Combo.Input("camera_source", display_name="카메라 참조 영상", options=[NONE] + VISUAL_SOURCES[9:],
                tooltip="선택하면 아래 카메라 움직임 대신 해당 영상의 카메라 움직임을 참조합니다."),
            io.Combo.Input("music_source", display_name="음악 참조 오디오", options=[NONE] + [f"<Audio {i}>" for i in range(1, 4)],
                tooltip="선택하면 아래 배경음악 대신 해당 오디오의 음악 스타일을 참조합니다. 원본을 복사하지 않습니다. 영상에 연결한 오디오가 먼저 번호를 받습니다."),
        ]
        inputs.extend(io.Combo.Input(name, display_name=label, options=list(choices),
                                    optional=name == "camera_direction")
                      for name, (label, choices) in OPTIONS.items())
        inputs.append(io.String.Input("prompt_details", default="{}", optional=True,
            dynamic_prompts=False, extra_dict={"h3_detail_fields": DETAIL_FIELDS},
            tooltip="버튼 UI의 시간·추가 프롬프트 설정"))
        return io.Schema(
            node_id="MiniMaxH3RefPromptBuilder",
            display_name="MiniMax H3 REF 프롬프트 선택기",
            category="MiniMax H3/prompt",
            description="한글 옵션으로 단일 샷 영문 REF 프롬프트를 만듭니다. prompt 출력을 MiniMax H3 Reference to Video의 prompt에 연결하세요. 선택한 태그와 실제 참조 입력 순서를 맞춰야 합니다.",
            inputs=inputs,
            outputs=[io.String.Output(display_name="prompt")],
        )

    @classmethod
    def execute(cls, subject_source, background_source, camera_source, music_source,
                subject_kind, action, framing, camera, lighting, style, soundscape, music,
                camera_direction="지정 안 함", prompt_details="{}"):
        details, fields = parse_details(prompt_details)
        for value, allowed in (
            (subject_source, VISUAL_SOURCES), (background_source, [NONE] + VISUAL_SOURCES),
            (camera_source, [NONE] + VISUAL_SOURCES[9:]),
            (music_source, [NONE] + [f"<Audio {i}>" for i in range(1, 4)]),
        ):
            if value not in allowed:
                raise ValueError(f"지원하지 않는 참조 태그: {value}")
        selected = dict(subject_kind=subject_kind, action=action, framing=framing, camera=camera,
                        lighting=lighting, style=style, soundscape=soundscape, music=music,
                        camera_direction=camera_direction)
        phrases = {name: OPTIONS[name][1][value] for name, value in selected.items()}
        definitions = [f"<Subject 1> is {phrases['subject_kind']} visible in {subject_source}; its recognizable appearance, proportions, colors, and surface details define the subject's visual identity."]
        retention = ["<Subject 1> (appears in [Shot 1]): fully_preserved - retain the defined visual identity while performing the target action."]
        setting = "The setting is a simple open space with an uncluttered background and a clearly defined ground plane."
        if background_source != NONE:
            definitions.append(f"<Subject 2> is the environment visible in {background_source}, providing the background layout, spatial arrangement, and recognizable environmental features.")
            retention.append("<Subject 2> (appears in [Shot 1]): fully_preserved - preserve the environment's layout and recognizable features under the target lighting.")
            setting = "The setting is <Subject 2>; its referenced layout surrounds <Subject 1>, with foreground and background elements retaining their spatial relationships."
        camera_text = phrases["camera"] + "."
        if camera_source != NONE:
            definitions.append(f"{camera_source} provides camera motion for the single target shot; its subjects and cuts are not reused.")
            retention.append(f"{camera_source} (camera movement in [Shot 1]): partially_preserved - follow the source camera trajectory and pace within one continuous shot.")
            camera_text = f"The camera follows the movement direction and pace of {camera_source}, adapting its framing to keep <Subject 1> visible in one continuous shot."
        music_text = phrases["music"]
        audio_in_shot = ""
        if music_source != NONE:
            definitions.append(f"{music_source} is the musical style and instrumental texture reference for the audience-only score.")
            retention.append(f"{music_source}: reference - generate new instrumental music guided by its musical character without copying the signal or vocal content.")
            music_text = f"New instrumental background music follows the instrumentation, tempo, and dynamics of {music_source}, remaining behind the scene sounds and resolving at the end."
            audio_in_shot = f"An audience-only instrumental score guided by {music_source} accompanies the shot from its opening and remains continuous as the action develops."
        elif music != "없음":
            audio_in_shot = music_text
        if "subject_kind" in fields:
            definitions[0] = describe_interval(definitions[0], fields["subject_kind"], "Subject appearance")
        setting = describe_interval(setting, fields.get("background_source", {}), "Environment")
        camera_text = describe_interval(camera_text, fields.get("camera", {}), "Camera movement")
        music_text = describe_interval(music_text, fields.get("music", {}), "Background music")
        if "music" in fields:
            audio_in_shot = music_text if music_text != "N/A" else ""
        for name in ("framing", "camera_direction", "lighting", "style", "soundscape"):
            phrases[name] = describe_interval(phrases[name], fields.get(name, {}), name.replace("_", " ").capitalize())
        action_text = describe_interval(f"<Subject 1> {phrases['action']}.", fields.get("action", {}), "Subject action")
        task = "reference generation + audio reference" if music_source != NONE else "reference generation"
        summary = f"[{task}] A single continuous shot shows <Subject 1> performing a simple action"
        summary += " within <Subject 2>." if background_source != NONE else " in an uncluttered setting."
        if camera_source != NONE:
            summary += f" Camera motion is guided by {camera_source}."
        if music_source != NONE:
            summary += f" The score references {music_source}."
        direction_text = phrases["camera_direction"] + " " if phrases["camera_direction"] else ""
        speech_text = "" if any(entry.get("prompt", "").strip() for entry in fields.values()) else "No dialogue, narration, or singing is introduced. "
        detail = (
            f"{phrases['style']}\n[Shot 1] {phrases['framing']}. "
            f"{direction_text}"
            f"<Subject 1> is clearly recognizable through the appearance established by {subject_source}. "
            f"{setting} {phrases['lighting']}. "
            "At the opening, the subject is clearly separated from the background, allowing its outline, relative scale, and visible surface details to be read. "
            "The arrangement leaves enough space for the action to unfold without obscuring the subject behind foreground elements. "
            f"As the shot progresses, {action_text} "
            "The movement develops gradually from the opening state, with a clear beginning, an uninterrupted middle phase, and a settled final pose. "
            "Its proportions and identifying features remain consistent as the viewpoint changes. "
            "Visible contact with the ground or surrounding surfaces stays physically coherent, and shadows follow the same lighting direction throughout. "
            f"{camera_text} "
            "The framing remains readable during the movement, allowing the viewer to follow the subject's position relative to the environment. "
            "Nearer surfaces and distant background details maintain a coherent sense of depth, with any visible parallax following the camera movement. "
            "Focus remains on the subject's defining details, while the background supports the composition without drawing attention away from the main action. "
            "The chosen light reveals shape and texture continuously; highlights and shaded areas evolve smoothly with the visible motion. "
            "There are no abrupt changes of location or unexplained substitutions of the subject during the shot. "
            f"{phrases['soundscape']} {audio_in_shot} "
            f"{speech_text}"
            "As the action concludes, the subject settles naturally and the composition remains stable long enough to read the final state. "
            "The ending grows directly from the preceding movement, preserving the same subject, environment, and lighting through the last frame. "
            "The shot remains continuous throughout, with no intervening cut or sudden transition to another scene."
        )
        if details:
            summary += f" The target duration is {details.get('duration', 5):g} seconds."
        sections = {
            "subject_definitions": "\n".join(definitions), "summary": summary,
            "retention_analysis": "\n".join(retention), "detailed_description": detail,
            "overall_soundscape": phrases["soundscape"], "non_diegetic_music": music_text,
        }
        prompt = "\n\n".join(f"{name}:\n{body}" for name, body in sections.items())
        return io.NodeOutput(prompt)


class MiniMaxH3PromptExtension(ComfyExtension):
    async def get_node_list(self):
        return [MiniMaxH3RefPromptBuilder]


async def comfy_entrypoint():
    return MiniMaxH3PromptExtension()
