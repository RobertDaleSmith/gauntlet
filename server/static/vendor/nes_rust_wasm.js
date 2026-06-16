/**
 * @enum {0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15}
 */
export const Button = Object.freeze({
    Poweroff: 0, "0": "Poweroff",
    Reset: 1, "1": "Reset",
    Select: 2, "2": "Select",
    Start: 3, "3": "Start",
    Joypad1A: 4, "4": "Joypad1A",
    Joypad1B: 5, "5": "Joypad1B",
    Joypad1Up: 6, "6": "Joypad1Up",
    Joypad1Down: 7, "7": "Joypad1Down",
    Joypad1Left: 8, "8": "Joypad1Left",
    Joypad1Right: 9, "9": "Joypad1Right",
    Joypad2A: 10, "10": "Joypad2A",
    Joypad2B: 11, "11": "Joypad2B",
    Joypad2Up: 12, "12": "Joypad2Up",
    Joypad2Down: 13, "13": "Joypad2Down",
    Joypad2Left: 14, "14": "Joypad2Left",
    Joypad2Right: 15, "15": "Joypad2Right",
});

/**
 * `WasmNes` is an interface between user JavaScript code and
 * WebAssembly NES emulator. The following code is example
 * JavaScript user code.
 *
 * ```ignore
 * // Create NES
 * const nes = WasmNes.new();
 *
 * // Load Rom
 * nes.set_rom(new Uint8Array(romArrayBuffer));
 *
 * // Set up Audio
 * const audioContext = AudioContext || webkitAudioContext;
 * const bufferLength = 4096;
 * const context = new audioContext({sampleRate: 44100});
 * const scriptProcessor = context.createScriptProcessor(bufferLength, 0, 1);
 * scriptProcessor.onaudioprocess = e => {
 *   const data = e.outputBuffer.getChannelData(0);
 *   nes.update_sample_buffer(data);
 * };
 * scriptProcessor.connect(context.destination);
 *
 * // Set up screen resources
 * const width = 256;
 * const height = 240;
 * const canvas = document.createElement('canvas');
 * const ctx = canvas.getContext('2d');
 * const imageData = ctx.createImageData(width, height);
 * const pixels = new Uint8Array(imageData.data.buffer);
 *
 * // animation frame loop
 * const stepFrame = () => {
 *   requestAnimationFrame(stepFrame);
 *   // Run emulator until screen is refreshed
 *   nes.step_frame();
 *   // Load screen pixels and render to canvas
 *   nes.update_pixels(pixels);
 *   ctx.putImageData(imageData, 0, 0);
 * };
 *
 * // Go!
 * nes.bootup();
 * stepFrame();
 * ```
 */
export class WasmNes {
    static __wrap(ptr) {
        const obj = Object.create(WasmNes.prototype);
        obj.__wbg_ptr = ptr;
        WasmNesFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        WasmNesFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_wasmnes_free(ptr, 0);
    }
    /**
     * Boots up
     */
    bootup() {
        wasm.wasmnes_bootup(this.__wbg_ptr);
    }
    /**
     * Creates a `WasmNes`
     * @returns {WasmNes}
     */
    static new() {
        const ret = wasm.wasmnes_new();
        return WasmNes.__wrap(ret);
    }
    /**
     * Presses a pad button
     *
     * # Arguments
     * * `button`
     * @param {Button} button
     */
    press_button(button) {
        wasm.wasmnes_press_button(this.__wbg_ptr, button);
    }
    /**
     * Releases a pad button
     *
     * # Arguments
     * * `buffer`
     * @param {Button} button
     */
    release_button(button) {
        wasm.wasmnes_release_button(this.__wbg_ptr, button);
    }
    /**
     * Resets
     */
    reset() {
        wasm.wasmnes_reset(this.__wbg_ptr);
    }
    /**
     * Sets up NES rom
     *
     * # Arguments
     * * `rom` Rom image binary `Uint8Array`
     * @param {Uint8Array} contents
     */
    set_rom(contents) {
        const ptr0 = passArray8ToWasm0(contents, wasm.__wbindgen_malloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.wasmnes_set_rom(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * Executes a CPU cycle
     */
    step() {
        wasm.wasmnes_step(this.__wbg_ptr);
    }
    /**
     * Executes a PPU (screen refresh) frame
     */
    step_frame() {
        wasm.wasmnes_step_frame(this.__wbg_ptr);
    }
    /**
     * Copies RGB pixels of screen to passed RGBA pixels.
     * The RGBA pixels length should be
     * 245760 = 256(width) * 240(height) * 4(RGBA).
     * A channel will be filled with 255(opaque).
     *
     * # Arguments
     * * `pixels` RGBA pixels `Uint8Array` or `Uint8ClampedArray`
     * @param {Uint8Array} pixels
     */
    update_pixels(pixels) {
        var ptr0 = passArray8ToWasm0(pixels, wasm.__wbindgen_malloc);
        var len0 = WASM_VECTOR_LEN;
        wasm.wasmnes_update_pixels(this.__wbg_ptr, ptr0, len0, pixels);
    }
    /**
     * Copies audio buffer to passed `Float32Array` buffer.
     * The length should be 4096.
     *
     * # Arguments
     * * `buffer` Audio buffer `Float32Array`
     * @param {Float32Array} buffer
     */
    update_sample_buffer(buffer) {
        var ptr0 = passArrayF32ToWasm0(buffer, wasm.__wbindgen_malloc);
        var len0 = WASM_VECTOR_LEN;
        wasm.wasmnes_update_sample_buffer(this.__wbg_ptr, ptr0, len0, buffer);
    }
}
if (Symbol.dispose) WasmNes.prototype[Symbol.dispose] = WasmNes.prototype.free;
function __wbg_get_imports() {
    const import0 = {
        __proto__: null,
        __wbg___wbindgen_copy_to_typed_array_c5728021fabd0236: function(arg0, arg1, arg2) {
            new Uint8Array(arg2.buffer, arg2.byteOffset, arg2.byteLength).set(getArrayU8FromWasm0(arg0, arg1));
        },
        __wbg___wbindgen_throw_ea4887a5f8f9a9db: function(arg0, arg1) {
            throw new Error(getStringFromWasm0(arg0, arg1));
        },
        __wbindgen_init_externref_table: function() {
            const table = wasm.__wbindgen_externrefs;
            const offset = table.grow(4);
            table.set(0, undefined);
            table.set(offset + 0, undefined);
            table.set(offset + 1, null);
            table.set(offset + 2, true);
            table.set(offset + 3, false);
        },
    };
    return {
        __proto__: null,
        "./nes_rust_wasm_bg.js": import0,
    };
}

const WasmNesFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_wasmnes_free(ptr, 1));

function getArrayU8FromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return getUint8ArrayMemory0().subarray(ptr / 1, ptr / 1 + len);
}

let cachedFloat32ArrayMemory0 = null;
function getFloat32ArrayMemory0() {
    if (cachedFloat32ArrayMemory0 === null || cachedFloat32ArrayMemory0.byteLength === 0) {
        cachedFloat32ArrayMemory0 = new Float32Array(wasm.memory.buffer);
    }
    return cachedFloat32ArrayMemory0;
}

function getStringFromWasm0(ptr, len) {
    return decodeText(ptr >>> 0, len);
}

let cachedUint8ArrayMemory0 = null;
function getUint8ArrayMemory0() {
    if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
        cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
    }
    return cachedUint8ArrayMemory0;
}

function passArray8ToWasm0(arg, malloc) {
    const ptr = malloc(arg.length * 1, 1) >>> 0;
    getUint8ArrayMemory0().set(arg, ptr / 1);
    WASM_VECTOR_LEN = arg.length;
    return ptr;
}

function passArrayF32ToWasm0(arg, malloc) {
    const ptr = malloc(arg.length * 4, 4) >>> 0;
    getFloat32ArrayMemory0().set(arg, ptr / 4);
    WASM_VECTOR_LEN = arg.length;
    return ptr;
}

let cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
cachedTextDecoder.decode();
const MAX_SAFARI_DECODE_BYTES = 2146435072;
let numBytesDecoded = 0;
function decodeText(ptr, len) {
    numBytesDecoded += len;
    if (numBytesDecoded >= MAX_SAFARI_DECODE_BYTES) {
        cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
        cachedTextDecoder.decode();
        numBytesDecoded = len;
    }
    return cachedTextDecoder.decode(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}

let WASM_VECTOR_LEN = 0;

let wasmModule, wasmInstance, wasm;
function __wbg_finalize_init(instance, module) {
    wasmInstance = instance;
    wasm = instance.exports;
    wasmModule = module;
    cachedFloat32ArrayMemory0 = null;
    cachedUint8ArrayMemory0 = null;
    wasm.__wbindgen_start();
    return wasm;
}

async function __wbg_load(module, imports) {
    if (typeof Response === 'function' && module instanceof Response) {
        if (typeof WebAssembly.instantiateStreaming === 'function') {
            try {
                return await WebAssembly.instantiateStreaming(module, imports);
            } catch (e) {
                const validResponse = module.ok && expectedResponseType(module.type);

                if (validResponse && module.headers.get('Content-Type') !== 'application/wasm') {
                    console.warn("`WebAssembly.instantiateStreaming` failed because your server does not serve Wasm with `application/wasm` MIME type. Falling back to `WebAssembly.instantiate` which is slower. Original error:\n", e);

                } else { throw e; }
            }
        }

        const bytes = await module.arrayBuffer();
        return await WebAssembly.instantiate(bytes, imports);
    } else {
        const instance = await WebAssembly.instantiate(module, imports);

        if (instance instanceof WebAssembly.Instance) {
            return { instance, module };
        } else {
            return instance;
        }
    }

    function expectedResponseType(type) {
        switch (type) {
            case 'basic': case 'cors': case 'default': return true;
        }
        return false;
    }
}

function initSync(module) {
    if (wasm !== undefined) return wasm;


    if (module !== undefined) {
        if (Object.getPrototypeOf(module) === Object.prototype) {
            ({module} = module)
        } else {
            console.warn('using deprecated parameters for `initSync()`; pass a single object instead')
        }
    }

    const imports = __wbg_get_imports();
    if (!(module instanceof WebAssembly.Module)) {
        module = new WebAssembly.Module(module);
    }
    const instance = new WebAssembly.Instance(module, imports);
    return __wbg_finalize_init(instance, module);
}

async function __wbg_init(module_or_path) {
    if (wasm !== undefined) return wasm;


    if (module_or_path !== undefined) {
        if (Object.getPrototypeOf(module_or_path) === Object.prototype) {
            ({module_or_path} = module_or_path)
        } else {
            console.warn('using deprecated parameters for the initialization function; pass a single object instead')
        }
    }

    if (module_or_path === undefined) {
        module_or_path = new URL('nes_rust_wasm_bg.wasm', import.meta.url);
    }
    const imports = __wbg_get_imports();

    if (typeof module_or_path === 'string' || (typeof Request === 'function' && module_or_path instanceof Request) || (typeof URL === 'function' && module_or_path instanceof URL)) {
        module_or_path = fetch(module_or_path);
    }

    const { instance, module } = await __wbg_load(await module_or_path, imports);

    return __wbg_finalize_init(instance, module);
}

export { initSync, __wbg_init as default };
