const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');

test('DOM panel forwards middle gestures and leaves editing gestures alone', async () => {
    const listeners = {};
    const forwarded = [];
    let extension;
    const stop = new Error('Stop before rendering');
    const root = {
        addEventListener(type, fn, options) { listeners[type] = { fn, options }; },
        attachShadow() { throw stop; },
    };
    const app = {
        registerExtension(value) { extension = value; },
        canvas: { canvas: { dispatchEvent(event) { forwarded.push(event); } } },
    };
    class PointerEvent {
        constructor(type, source) { Object.assign(this, source); this.type = type; }
    }
    const source = fs.readFileSync(require('node:path').join(__dirname, '../web/prompt_builder.js'), 'utf8');
    vm.runInNewContext(source.replace(/^import .*;\r?\n/, ''), {
        app, PointerEvent, document: { createElement() { return root; } },
    });
    function Node() { this.widgets = []; }
    await extension.beforeRegisterNodeDef(Node, {
        name: 'MiniMaxH3RefPromptBuilder',
        input: { required: { prompt_details: ['STRING', { h3_detail_fields: {} }] } },
    });
    assert.throws(() => new Node().onNodeCreated(), error => error === stop);
    for (const [type, button, buttons] of [
        ['pointerdown', 1, 4], ['pointermove', -1, 4], ['pointerup', 1, 0],
    ]) {
        let prevented = false, stopped = false;
        const event = { type, button, buttons, pointerId: 7, isPrimary: true, clientX: 120, clientY: 85,
            preventDefault() { prevented = true; }, stopPropagation() { stopped = true; } };
        assert.equal(listeners[type].options.capture, true);
        listeners[type].fn(event);
        assert.ok(prevented && stopped);
        assert.equal(forwarded.at(-1).pointerId, 7);
        assert.equal(forwarded.at(-1).clientX, 120);
        assert.equal(forwarded.at(-1).type, type);
    }
    for (const button of [0, 2]) {
        listeners.pointerdown.fn({ button, buttons: button === 0 ? 1 : 2 });
    }
    listeners.pointermove.fn({ button: -1, buttons: 0 });
    assert.equal(forwarded.length, 3);
    app.canvas = null;
    listeners.pointerdown.fn({ button: 1, buttons: 4 });
    assert.equal(forwarded.length, 3);
});
