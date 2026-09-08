import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "minimax.h3.promptButtons",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "MiniMaxH3RefPromptBuilder") return;
        const inputs = { ...nodeData.input.required, ...nodeData.input.optional };
        const detailFields = inputs.prompt_details[1].h3_detail_fields;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = created?.apply(this, arguments);
            const node = this;
            const widgets = Object.fromEntries(node.widgets.map((widget) => [widget.name, widget]));
            const choices = Object.entries(inputs).filter(([, definition]) => definition[0] === "COMBO");
            const root = document.createElement("div");
            root.addEventListener("keydown", (event) => event.stopPropagation());
            const shadow = root.attachShadow({ mode: "open" });
            shadow.innerHTML = `<style>
                :host { display:block; height:100%; color:#e7eaf0; font:13px/1.5 system-ui,sans-serif; }
                * { box-sizing:border-box; }
                .panel { height:100%; overflow:auto; padding:14px; background:#20242d; border-radius:10px; }
                h3 { margin:0 0 10px; font-size:16px; }
                .tabs,.choices { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0; }
                button { border:1px solid #536074; border-radius:7px; padding:7px 10px; color:inherit; background:#303846; cursor:pointer; font:inherit; }
                button:hover { background:#424f62; }
                button[aria-pressed=true] { background:#205a93; border-color:#77bafa; }
                button:focus-visible,input:focus-visible,textarea:focus-visible { outline:2px solid #a0d1ff; outline-offset:2px; }
                button:disabled { opacity:.5; cursor:default; }
                .tabs button { font-size:12px; padding:5px 8px; }
                label { display:block; margin:10px 0 4px; }
                input,textarea { color:inherit; background:#141922; border:1px solid #536074; border-radius:6px; padding:8px; font:inherit; }
                input[type=number] { width:110px; }
                textarea { width:100%; min-height:116px; resize:vertical; }
                .times { display:flex; gap:16px; flex-wrap:wrap; }
                .hint { color:#b1bccd; font-size:12px; margin:6px 0; }
                .error { color:#ffb3b3; min-height:20px; }
                .selection { color:#9fd1ff; }
            </style><div class="panel"></div>`;
            const panel = shadow.querySelector(".panel");
            let active = "action";

            function readDetails() {
                return JSON.parse(widgets.prompt_details.value || "{}");
            }
            function change(callback) {
                node.graph?.beforeChange();
                callback();
                node.graph?.afterChange();
                node.setDirtyCanvas(true, true);
            }
            function saveField(name, patch) {
                change(() => {
                    const details = readDetails();
                    details.fields ??= {};
                    const entry = { ...details.fields[name], ...patch };
                    for (const key of Object.keys(entry)) {
                        if (entry[key] === undefined || entry[key] === "") delete entry[key];
                    }
                    if (Object.keys(entry).length) details.fields[name] = entry;
                    else delete details.fields[name];
                    widgets.prompt_details.value = JSON.stringify(details);
                });
                validate();
            }
            function element(tag, text, parent = panel) {
                const el = document.createElement(tag);
                if (text !== undefined) el.textContent = text;
                parent.append(el);
                return el;
            }
            function validate() {
                const message = panel.querySelector(".error");
                try {
                    const details = readDetails();
                    const duration = "duration" in details ? details.duration : 5;
                    if (!Number.isFinite(duration) || duration <= 0 || duration > 150) throw new Error("영상 길이를 0초 초과, 150초 이하로 입력하세요.");
                    for (const [name, entry] of Object.entries(details.fields ?? {})) {
                        if ("start" in entry || "end" in entry) {
                            if (!(Number.isFinite(entry.start) && Number.isFinite(entry.end) && 0 <= entry.start && entry.start < entry.end && entry.end <= duration)) {
                                throw new Error(`${inputs[name][1].display_name}: 0 ≤ 시작 < 종료 ≤ 영상 길이를 지켜주세요.`);
                            }
                        }
                    }
                    message.textContent = "";
                } catch (error) {
                    message.textContent = error.message;
                }
            }
            function render() {
                panel.replaceChildren();
                element("h3", "H3 REF 프롬프트");
                let details;
                try { details = readDetails(); }
                catch {
                    element("p", "저장된 시간·프롬프트 설정을 읽을 수 없습니다.").className = "error";
                    const reset = element("button", "시간·추가 프롬프트 초기화");
                    reset.onclick = () => { change(() => { widgets.prompt_details.value = "{}"; }); render(); };
                    return;
                }
                const durationLabel = element("label", "영상 길이 (초) ");
                const duration = element("input", undefined, durationLabel);
                duration.type = "number";
                duration.min = "0.001"; duration.max = "150"; duration.step = "0.1";
                duration.value = details.duration === undefined ? 5 : (details.duration ?? "");
                duration.oninput = () => {
                    change(() => {
                        const current = readDetails();
                        current.duration = duration.valueAsNumber;
                        widgets.prompt_details.value = JSON.stringify(current);
                    });
                    validate();
                };
                element("p", "프롬프트의 시간 기준입니다. 실제 생성 길이도 Reference to Video 노드에서 맞춰주세요.").className = "hint";
                const tabs = element("div"); tabs.className = "tabs";
                for (const [name, definition] of choices) {
                    const tab = element("button", definition[1].display_name ?? name, tabs);
                    tab.setAttribute("aria-pressed", String(name === active));
                    tab.onclick = () => { active = name; render(); };
                }
                const widget = widgets[active];
                const definition = inputs[active];
                element("h3", definition[1].display_name ?? active);
                element("p", `선택: ${widget.value}`).className = "selection";
                const linked = node.inputs?.some((input) => input.name === active && input.link != null);
                const overridden = (active === "camera" && widgets.camera_source.value !== "사용 안 함") ||
                    (active === "music" && widgets.music_source.value !== "사용 안 함");
                if (linked) element("p", "연결된 입력 노드의 선택값을 사용합니다.").className = "hint";
                if (overridden) element("p", "참조 자료가 선택되어 있어 아래 프리셋 대신 참조를 사용합니다. 시간과 추가 설명은 적용됩니다.").className = "hint";
                const buttons = element("div"); buttons.className = "choices";
                for (const value of definition[1].options) {
                    const button = element("button", String(value), buttons);
                    button.setAttribute("aria-pressed", String(widget.value === value));
                    button.disabled = linked || overridden;
                    button.onclick = () => {
                        change(() => { widget.value = value; widget.callback?.(value); });
                        render();
                    };
                }
                if (definition[1].tooltip) element("p", definition[1].tooltip).className = "hint";
                if (active in detailFields) {
                    const entry = details.fields?.[active] ?? {};
                    if (detailFields[active]) {
                        const checkLabel = element("label");
                        const check = element("input", undefined, checkLabel);
                        check.type = "checkbox"; check.checked = "start" in entry || "end" in entry;
                        checkLabel.append(" 적용 시간 지정 (끄면 전체 영상)");
                        check.onchange = () => {
                            saveField(active, check.checked ? { start: 0, end: readDetails().duration ?? 5 } : { start: undefined, end: undefined });
                            render();
                        };
                        if (check.checked) {
                            const row = element("div"); row.className = "times";
                            for (const [key, title] of [["start", "시작 (초)"], ["end", "종료 (초)"]]) {
                                const label = element("label", title + " ", row);
                                const input = element("input", undefined, label);
                                input.type = "number"; input.min = "0"; input.max = details.duration ?? 5; input.step = "0.1";
                                input.value = entry[key] ?? "";
                                input.oninput = () => saveField(active, { [key]: input.valueAsNumber });
                            }
                        }
                    }
                    const label = element("label", "추가 프롬프트 (선택)");
                    const textarea = element("textarea", undefined, label);
                    textarea.value = entry.prompt ?? "";
                    textarea.placeholder = "예: Slowly raise the right hand, pause, then lower it.";
                    textarea.oninput = () => saveField(active, { prompt: textarea.value });
                    element("p", "선택한 내용에 덧붙입니다. 영문 권장 · 자동 번역 없음. 상충하는 지시는 피해주세요.").className = "hint";
                }
                element("p", "").className = "error";
                validate();
            }

            for (const widget of Object.values(widgets)) {
                widget.type = "h3-hidden";
                widget.computeSize = () => [0, -4];
                widget.draw = () => {};
                if (widget.inputEl) widget.inputEl.style.display = "none";
            }
            const dom = node.addDOMWidget("h3_buttons", "h3-buttons", root, { serialize: false, hideOnZoom: false });
            dom.serialize = false;
            dom.computeSize = () => [480, 650];
            node.setSize([520, 710]);
            const configure = node.onConfigure;
            node.onConfigure = function () {
                const value = configure?.apply(this, arguments);
                render();
                return value;
            };
            render();
            return result;
        };
    },
});
