# MiniMax H3 REF 프롬프트 선택기

저장소: [taro6222/minimax_h3_prompt_builder](https://github.com/taro6222/minimax_h3_prompt_builder)

ComfyUI의 `custom_nodes` 폴더에서 설치합니다.

```sh
git clone https://github.com/taro6222/minimax_h3_prompt_builder.git
```

ComfyUI를 재시작한 뒤 `MiniMax H3 REF 프롬프트 선택기`를 검색해 추가합니다.
별도 패키지 설치나 API 키가 필요하지 않습니다.

1. 주인공 참조를 선택합니다. 기본값은 `<Picture 1>`입니다.
2. 주인공 종류, 동작, 구도, 카메라, 조명, 스타일, 환경음, 음악을 선택합니다.
3. 필요하면 배경 참조, 카메라 참조 영상, 음악 참조 오디오를 선택합니다.
4. `prompt` 출력을 `MiniMax H3 Reference to Video`의 `prompt` 입력에 연결합니다.
   입력이 텍스트 위젯이면 위젯 메뉴에서 입력 소켓으로 변환합니다.
5. 생성 문장을 먼저 보려면 `Preview as Text`에 연결하고 실행합니다.

한글 선택 항목으로 영문 단일 샷 프롬프트를 구성합니다. 실제 참조 미디어는 기존
Reference to Video 노드에 연결해야 합니다. 이 노드는 자료를 분석하거나 연결 여부를
확인하지 않으므로, 자료에 맞는 주인공 종류와 동작을 선택하세요.

참조 번호는 실제 입력의 종류별 순서와 맞춰야 합니다. 특히 현재 로컬 H3 노드는
영상에 연결한 오디오를 영상 순서대로 먼저 번호 매기고, 독립 오디오를 그 뒤에
번호 매깁니다. `<Video 1>`의 사운드트랙과 독립 오디오 하나를 사용하면 독립 오디오는
`<Audio 2>`입니다. 빈 입력은 번호를 차지하지 않습니다.

카메라 참조 영상을 선택하면 수동 카메라 옵션을 대체합니다. 음악 참조 오디오를
선택하면 음악 프리셋을 대체하며, 원본 복사가 아닌 새 음악의 스타일 참조로 작성합니다.
현재 범위는 주인공 하나, 배경 하나, 단일 샷입니다. 대사, 다중 샷, 키프레임 지정,
원본 영상 편집·연장은 포함하지 않습니다.

[공식 REF 작성 가이드](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md)의
6개 섹션, 참조 역할, 보존 마커에 맞춰 구성한 템플릿입니다.
실제 영상 품질 및 모델의 프롬프트 준수 여부는 별도로 생성 검증해야 합니다.

이 폴더는 ComfyUI 본체와 분리된 Git 저장소로 관리합니다.
