function noop() { }
function assign(tar, src) {
    // @ts-ignore
    for (const k in src)
        tar[k] = src[k];
    return tar;
}
function run(fn) {
    return fn();
}
function blank_object() {
    return Object.create(null);
}
function run_all(fns) {
    fns.forEach(run);
}
function is_function(thing) {
    return typeof thing === 'function';
}
function safe_not_equal(a, b) {
    return a != a ? b == b : a !== b || ((a && typeof a === 'object') || typeof a === 'function');
}
function is_empty(obj) {
    return Object.keys(obj).length === 0;
}
function create_slot(definition, ctx, $$scope, fn) {
    if (definition) {
        const slot_ctx = get_slot_context(definition, ctx, $$scope, fn);
        return definition[0](slot_ctx);
    }
}
function get_slot_context(definition, ctx, $$scope, fn) {
    return definition[1] && fn
        ? assign($$scope.ctx.slice(), definition[1](fn(ctx)))
        : $$scope.ctx;
}
function get_slot_changes(definition, $$scope, dirty, fn) {
    if (definition[2] && fn) {
        const lets = definition[2](fn(dirty));
        if ($$scope.dirty === undefined) {
            return lets;
        }
        if (typeof lets === 'object') {
            const merged = [];
            const len = Math.max($$scope.dirty.length, lets.length);
            for (let i = 0; i < len; i += 1) {
                merged[i] = $$scope.dirty[i] | lets[i];
            }
            return merged;
        }
        return $$scope.dirty | lets;
    }
    return $$scope.dirty;
}
function update_slot(slot, slot_definition, ctx, $$scope, dirty, get_slot_changes_fn, get_slot_context_fn) {
    const slot_changes = get_slot_changes(slot_definition, $$scope, dirty, get_slot_changes_fn);
    if (slot_changes) {
        const slot_context = get_slot_context(slot_definition, ctx, $$scope, get_slot_context_fn);
        slot.p(slot_context, slot_changes);
    }
}

// Track which nodes are claimed during hydration. Unclaimed nodes can then be removed from the DOM
// at the end of hydration without touching the remaining nodes.
let is_hydrating = false;
function start_hydrating() {
    is_hydrating = true;
}
function end_hydrating() {
    is_hydrating = false;
}
function upper_bound(low, high, key, value) {
    // Return first index of value larger than input value in the range [low, high)
    while (low < high) {
        const mid = low + ((high - low) >> 1);
        if (key(mid) <= value) {
            low = mid + 1;
        }
        else {
            high = mid;
        }
    }
    return low;
}
function init_hydrate(target) {
    if (target.hydrate_init)
        return;
    target.hydrate_init = true;
    // We know that all children have claim_order values since the unclaimed have been detached
    const children = target.childNodes;
    /*
    * Reorder claimed children optimally.
    * We can reorder claimed children optimally by finding the longest subsequence of
    * nodes that are already claimed in order and only moving the rest. The longest
    * subsequence subsequence of nodes that are claimed in order can be found by
    * computing the longest increasing subsequence of .claim_order values.
    *
    * This algorithm is optimal in generating the least amount of reorder operations
    * possible.
    *
    * Proof:
    * We know that, given a set of reordering operations, the nodes that do not move
    * always form an increasing subsequence, since they do not move among each other
    * meaning that they must be already ordered among each other. Thus, the maximal
    * set of nodes that do not move form a longest increasing subsequence.
    */
    // Compute longest increasing subsequence
    // m: subsequence length j => index k of smallest value that ends an increasing subsequence of length j
    const m = new Int32Array(children.length + 1);
    // Predecessor indices + 1
    const p = new Int32Array(children.length);
    m[0] = -1;
    let longest = 0;
    for (let i = 0; i < children.length; i++) {
        const current = children[i].claim_order;
        // Find the largest subsequence length such that it ends in a value less than our current value
        // upper_bound returns first greater value, so we subtract one
        const seqLen = upper_bound(1, longest + 1, idx => children[m[idx]].claim_order, current) - 1;
        p[i] = m[seqLen] + 1;
        const newLen = seqLen + 1;
        // We can guarantee that current is the smallest value. Otherwise, we would have generated a longer sequence.
        m[newLen] = i;
        longest = Math.max(newLen, longest);
    }
    // The longest increasing subsequence of nodes (initially reversed)
    const lis = [];
    // The rest of the nodes, nodes that will be moved
    const toMove = [];
    let last = children.length - 1;
    for (let cur = m[longest] + 1; cur != 0; cur = p[cur - 1]) {
        lis.push(children[cur - 1]);
        for (; last >= cur; last--) {
            toMove.push(children[last]);
        }
        last--;
    }
    for (; last >= 0; last--) {
        toMove.push(children[last]);
    }
    lis.reverse();
    // We sort the nodes being moved to guarantee that their insertion order matches the claim order
    toMove.sort((a, b) => a.claim_order - b.claim_order);
    // Finally, we move the nodes
    for (let i = 0, j = 0; i < toMove.length; i++) {
        while (j < lis.length && toMove[i].claim_order >= lis[j].claim_order) {
            j++;
        }
        const anchor = j < lis.length ? lis[j] : null;
        target.insertBefore(toMove[i], anchor);
    }
}
function append(target, node) {
    if (is_hydrating) {
        init_hydrate(target);
        if ((target.actual_end_child === undefined) || ((target.actual_end_child !== null) && (target.actual_end_child.parentElement !== target))) {
            target.actual_end_child = target.firstChild;
        }
        if (node !== target.actual_end_child) {
            target.insertBefore(node, target.actual_end_child);
        }
        else {
            target.actual_end_child = node.nextSibling;
        }
    }
    else if (node.parentNode !== target) {
        target.appendChild(node);
    }
}
function insert(target, node, anchor) {
    if (is_hydrating && !anchor) {
        append(target, node);
    }
    else if (node.parentNode !== target || (anchor && node.nextSibling !== anchor)) {
        target.insertBefore(node, anchor || null);
    }
}
function detach(node) {
    node.parentNode.removeChild(node);
}
function destroy_each(iterations, detaching) {
    for (let i = 0; i < iterations.length; i += 1) {
        if (iterations[i])
            iterations[i].d(detaching);
    }
}
function element(name) {
    return document.createElement(name);
}
function text(data) {
    return document.createTextNode(data);
}
function space() {
    return text(' ');
}
function listen(node, event, handler, options) {
    node.addEventListener(event, handler, options);
    return () => node.removeEventListener(event, handler, options);
}
function attr(node, attribute, value) {
    if (value == null)
        node.removeAttribute(attribute);
    else if (node.getAttribute(attribute) !== value)
        node.setAttribute(attribute, value);
}
function set_custom_element_data(node, prop, value) {
    if (prop in node) {
        node[prop] = typeof node[prop] === 'boolean' && value === '' ? true : value;
    }
    else {
        attr(node, prop, value);
    }
}
function children(element) {
    return Array.from(element.childNodes);
}
function set_data(text, data) {
    data = '' + data;
    if (text.wholeText !== data)
        text.data = data;
}
function set_style(node, key, value, important) {
    node.style.setProperty(key, value, important ? 'important' : '');
}
function select_option(select, value) {
    for (let i = 0; i < select.options.length; i += 1) {
        const option = select.options[i];
        if (option.__value === value) {
            option.selected = true;
            return;
        }
    }
}
function select_value(select) {
    const selected_option = select.querySelector(':checked') || select.options[0];
    return selected_option && selected_option.__value;
}
// unfortunately this can't be a constant as that wouldn't be tree-shakeable
// so we cache the result instead
let crossorigin;
function is_crossorigin() {
    if (crossorigin === undefined) {
        crossorigin = false;
        try {
            if (typeof window !== 'undefined' && window.parent) {
                void window.parent.document;
            }
        }
        catch (error) {
            crossorigin = true;
        }
    }
    return crossorigin;
}
function add_resize_listener(node, fn) {
    const computed_style = getComputedStyle(node);
    if (computed_style.position === 'static') {
        node.style.position = 'relative';
    }
    const iframe = element('iframe');
    iframe.setAttribute('style', 'display: block; position: absolute; top: 0; left: 0; width: 100%; height: 100%; ' +
        'overflow: hidden; border: 0; opacity: 0; pointer-events: none; z-index: -1;');
    iframe.setAttribute('aria-hidden', 'true');
    iframe.tabIndex = -1;
    const crossorigin = is_crossorigin();
    let unsubscribe;
    if (crossorigin) {
        iframe.src = "data:text/html,<script>onresize=function(){parent.postMessage(0,'*')}</script>";
        unsubscribe = listen(window, 'message', (event) => {
            if (event.source === iframe.contentWindow)
                fn();
        });
    }
    else {
        iframe.src = 'about:blank';
        iframe.onload = () => {
            unsubscribe = listen(iframe.contentWindow, 'resize', fn);
        };
    }
    append(node, iframe);
    return () => {
        if (crossorigin) {
            unsubscribe();
        }
        else if (unsubscribe && iframe.contentWindow) {
            unsubscribe();
        }
        detach(iframe);
    };
}
function toggle_class(element, name, toggle) {
    element.classList[toggle ? 'add' : 'remove'](name);
}

let current_component;
function set_current_component(component) {
    current_component = component;
}
function get_current_component() {
    if (!current_component)
        throw new Error('Function called outside component initialization');
    return current_component;
}
function onMount(fn) {
    get_current_component().$$.on_mount.push(fn);
}

const dirty_components = [];
const binding_callbacks = [];
const render_callbacks = [];
const flush_callbacks = [];
const resolved_promise = Promise.resolve();
let update_scheduled = false;
function schedule_update() {
    if (!update_scheduled) {
        update_scheduled = true;
        resolved_promise.then(flush);
    }
}
function tick() {
    schedule_update();
    return resolved_promise;
}
function add_render_callback(fn) {
    render_callbacks.push(fn);
}
function add_flush_callback(fn) {
    flush_callbacks.push(fn);
}
let flushing = false;
const seen_callbacks = new Set();
function flush() {
    if (flushing)
        return;
    flushing = true;
    do {
        // first, call beforeUpdate functions
        // and update components
        for (let i = 0; i < dirty_components.length; i += 1) {
            const component = dirty_components[i];
            set_current_component(component);
            update(component.$$);
        }
        set_current_component(null);
        dirty_components.length = 0;
        while (binding_callbacks.length)
            binding_callbacks.pop()();
        // then, once components are updated, call
        // afterUpdate functions. This may cause
        // subsequent updates...
        for (let i = 0; i < render_callbacks.length; i += 1) {
            const callback = render_callbacks[i];
            if (!seen_callbacks.has(callback)) {
                // ...so guard against infinite loops
                seen_callbacks.add(callback);
                callback();
            }
        }
        render_callbacks.length = 0;
    } while (dirty_components.length);
    while (flush_callbacks.length) {
        flush_callbacks.pop()();
    }
    update_scheduled = false;
    flushing = false;
    seen_callbacks.clear();
}
function update($$) {
    if ($$.fragment !== null) {
        $$.update();
        run_all($$.before_update);
        const dirty = $$.dirty;
        $$.dirty = [-1];
        $$.fragment && $$.fragment.p($$.ctx, dirty);
        $$.after_update.forEach(add_render_callback);
    }
}
const outroing = new Set();
let outros;
function group_outros() {
    outros = {
        r: 0,
        c: [],
        p: outros // parent group
    };
}
function check_outros() {
    if (!outros.r) {
        run_all(outros.c);
    }
    outros = outros.p;
}
function transition_in(block, local) {
    if (block && block.i) {
        outroing.delete(block);
        block.i(local);
    }
}
function transition_out(block, local, detach, callback) {
    if (block && block.o) {
        if (outroing.has(block))
            return;
        outroing.add(block);
        outros.c.push(() => {
            outroing.delete(block);
            if (callback) {
                if (detach)
                    block.d(1);
                callback();
            }
        });
        block.o(local);
    }
}
function outro_and_destroy_block(block, lookup) {
    transition_out(block, 1, 1, () => {
        lookup.delete(block.key);
    });
}
function update_keyed_each(old_blocks, dirty, get_key, dynamic, ctx, list, lookup, node, destroy, create_each_block, next, get_context) {
    let o = old_blocks.length;
    let n = list.length;
    let i = o;
    const old_indexes = {};
    while (i--)
        old_indexes[old_blocks[i].key] = i;
    const new_blocks = [];
    const new_lookup = new Map();
    const deltas = new Map();
    i = n;
    while (i--) {
        const child_ctx = get_context(ctx, list, i);
        const key = get_key(child_ctx);
        let block = lookup.get(key);
        if (!block) {
            block = create_each_block(key, child_ctx);
            block.c();
        }
        else if (dynamic) {
            block.p(child_ctx, dirty);
        }
        new_lookup.set(key, new_blocks[i] = block);
        if (key in old_indexes)
            deltas.set(key, Math.abs(i - old_indexes[key]));
    }
    const will_move = new Set();
    const did_move = new Set();
    function insert(block) {
        transition_in(block, 1);
        block.m(node, next);
        lookup.set(block.key, block);
        next = block.first;
        n--;
    }
    while (o && n) {
        const new_block = new_blocks[n - 1];
        const old_block = old_blocks[o - 1];
        const new_key = new_block.key;
        const old_key = old_block.key;
        if (new_block === old_block) {
            // do nothing
            next = new_block.first;
            o--;
            n--;
        }
        else if (!new_lookup.has(old_key)) {
            // remove old block
            destroy(old_block, lookup);
            o--;
        }
        else if (!lookup.has(new_key) || will_move.has(new_key)) {
            insert(new_block);
        }
        else if (did_move.has(old_key)) {
            o--;
        }
        else if (deltas.get(new_key) > deltas.get(old_key)) {
            did_move.add(new_key);
            insert(new_block);
        }
        else {
            will_move.add(old_key);
            o--;
        }
    }
    while (o--) {
        const old_block = old_blocks[o];
        if (!new_lookup.has(old_block.key))
            destroy(old_block, lookup);
    }
    while (n)
        insert(new_blocks[n - 1]);
    return new_blocks;
}

function bind(component, name, callback) {
    const index = component.$$.props[name];
    if (index !== undefined) {
        component.$$.bound[index] = callback;
        callback(component.$$.ctx[index]);
    }
}
function create_component(block) {
    block && block.c();
}
function mount_component(component, target, anchor, customElement) {
    const { fragment, on_mount, on_destroy, after_update } = component.$$;
    fragment && fragment.m(target, anchor);
    if (!customElement) {
        // onMount happens before the initial afterUpdate
        add_render_callback(() => {
            const new_on_destroy = on_mount.map(run).filter(is_function);
            if (on_destroy) {
                on_destroy.push(...new_on_destroy);
            }
            else {
                // Edge case - component was destroyed immediately,
                // most likely as a result of a binding initialising
                run_all(new_on_destroy);
            }
            component.$$.on_mount = [];
        });
    }
    after_update.forEach(add_render_callback);
}
function destroy_component(component, detaching) {
    const $$ = component.$$;
    if ($$.fragment !== null) {
        run_all($$.on_destroy);
        $$.fragment && $$.fragment.d(detaching);
        // TODO null out other refs, including component.$$ (but need to
        // preserve final state?)
        $$.on_destroy = $$.fragment = null;
        $$.ctx = [];
    }
}
function make_dirty(component, i) {
    if (component.$$.dirty[0] === -1) {
        dirty_components.push(component);
        schedule_update();
        component.$$.dirty.fill(0);
    }
    component.$$.dirty[(i / 31) | 0] |= (1 << (i % 31));
}
function init(component, options, instance, create_fragment, not_equal, props, dirty = [-1]) {
    const parent_component = current_component;
    set_current_component(component);
    const $$ = component.$$ = {
        fragment: null,
        ctx: null,
        // state
        props,
        update: noop,
        not_equal,
        bound: blank_object(),
        // lifecycle
        on_mount: [],
        on_destroy: [],
        on_disconnect: [],
        before_update: [],
        after_update: [],
        context: new Map(parent_component ? parent_component.$$.context : options.context || []),
        // everything else
        callbacks: blank_object(),
        dirty,
        skip_bound: false
    };
    let ready = false;
    $$.ctx = instance
        ? instance(component, options.props || {}, (i, ret, ...rest) => {
            const value = rest.length ? rest[0] : ret;
            if ($$.ctx && not_equal($$.ctx[i], $$.ctx[i] = value)) {
                if (!$$.skip_bound && $$.bound[i])
                    $$.bound[i](value);
                if (ready)
                    make_dirty(component, i);
            }
            return ret;
        })
        : [];
    $$.update();
    ready = true;
    run_all($$.before_update);
    // `false` as a special case of no DOM component
    $$.fragment = create_fragment ? create_fragment($$.ctx) : false;
    if (options.target) {
        if (options.hydrate) {
            start_hydrating();
            const nodes = children(options.target);
            // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
            $$.fragment && $$.fragment.l(nodes);
            nodes.forEach(detach);
        }
        else {
            // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
            $$.fragment && $$.fragment.c();
        }
        if (options.intro)
            transition_in(component.$$.fragment);
        mount_component(component, options.target, options.anchor, options.customElement);
        end_hydrating();
        flush();
    }
    set_current_component(parent_component);
}
/**
 * Base class for Svelte components. Used when dev=false.
 */
class SvelteComponent {
    $destroy() {
        destroy_component(this, 1);
        this.$destroy = noop;
    }
    $on(type, callback) {
        const callbacks = (this.$$.callbacks[type] || (this.$$.callbacks[type] = []));
        callbacks.push(callback);
        return () => {
            const index = callbacks.indexOf(callback);
            if (index !== -1)
                callbacks.splice(index, 1);
        };
    }
    $set($$props) {
        if (this.$$set && !is_empty($$props)) {
            this.$$.skip_bound = true;
            this.$$set($$props);
            this.$$.skip_bound = false;
        }
    }
}

/* tmp/test/js-hex-editor-main/node_modules/@sveltejs/svelte-virtual-list/VirtualList.svelte generated by Svelte v3.38.3 */

function add_css$2() {
	var style = element("style");
	style.id = "svelte-1tqh76q-style";
	style.textContent = "svelte-virtual-list-viewport.svelte-1tqh76q{position:relative;overflow-y:auto;-webkit-overflow-scrolling:touch;display:block}svelte-virtual-list-contents.svelte-1tqh76q,svelte-virtual-list-row.svelte-1tqh76q{display:block}svelte-virtual-list-row.svelte-1tqh76q{overflow:hidden}";
	append(document.head, style);
}

function get_each_context$1(ctx, list, i) {
	const child_ctx = ctx.slice();
	child_ctx[23] = list[i];
	return child_ctx;
}

const get_default_slot_changes = dirty => ({ item: dirty & /*visible*/ 16 });
const get_default_slot_context = ctx => ({ item: /*row*/ ctx[23].data });

// (166:26) Missing template
function fallback_block(ctx) {
	let t;

	return {
		c() {
			t = text("Missing template");
		},
		m(target, anchor) {
			insert(target, t, anchor);
		},
		d(detaching) {
			if (detaching) detach(t);
		}
	};
}

// (164:2) {#each visible as row (row.index)}
function create_each_block$1(key_1, ctx) {
	let svelte_virtual_list_row;
	let t;
	let current;
	const default_slot_template = /*#slots*/ ctx[14].default;
	const default_slot = create_slot(default_slot_template, ctx, /*$$scope*/ ctx[13], get_default_slot_context);
	const default_slot_or_fallback = default_slot || fallback_block();

	return {
		key: key_1,
		first: null,
		c() {
			svelte_virtual_list_row = element("svelte-virtual-list-row");
			if (default_slot_or_fallback) default_slot_or_fallback.c();
			t = space();
			set_custom_element_data(svelte_virtual_list_row, "class", "svelte-1tqh76q");
			this.first = svelte_virtual_list_row;
		},
		m(target, anchor) {
			insert(target, svelte_virtual_list_row, anchor);

			if (default_slot_or_fallback) {
				default_slot_or_fallback.m(svelte_virtual_list_row, null);
			}

			append(svelte_virtual_list_row, t);
			current = true;
		},
		p(new_ctx, dirty) {
			ctx = new_ctx;

			if (default_slot) {
				if (default_slot.p && (!current || dirty & /*$$scope, visible*/ 8208)) {
					update_slot(default_slot, default_slot_template, ctx, /*$$scope*/ ctx[13], !current ? -1 : dirty, get_default_slot_changes, get_default_slot_context);
				}
			}
		},
		i(local) {
			if (current) return;
			transition_in(default_slot_or_fallback, local);
			current = true;
		},
		o(local) {
			transition_out(default_slot_or_fallback, local);
			current = false;
		},
		d(detaching) {
			if (detaching) detach(svelte_virtual_list_row);
			if (default_slot_or_fallback) default_slot_or_fallback.d(detaching);
		}
	};
}

function create_fragment$2(ctx) {
	let svelte_virtual_list_viewport;
	let svelte_virtual_list_contents;
	let each_blocks = [];
	let each_1_lookup = new Map();
	let svelte_virtual_list_viewport_resize_listener;
	let current;
	let mounted;
	let dispose;
	let each_value = /*visible*/ ctx[4];
	const get_key = ctx => /*row*/ ctx[23].index;

	for (let i = 0; i < each_value.length; i += 1) {
		let child_ctx = get_each_context$1(ctx, each_value, i);
		let key = get_key(child_ctx);
		each_1_lookup.set(key, each_blocks[i] = create_each_block$1(key, child_ctx));
	}

	return {
		c() {
			svelte_virtual_list_viewport = element("svelte-virtual-list-viewport");
			svelte_virtual_list_contents = element("svelte-virtual-list-contents");

			for (let i = 0; i < each_blocks.length; i += 1) {
				each_blocks[i].c();
			}

			set_style(svelte_virtual_list_contents, "padding-top", /*top*/ ctx[5] + "px");
			set_style(svelte_virtual_list_contents, "padding-bottom", /*bottom*/ ctx[6] + "px");
			set_custom_element_data(svelte_virtual_list_contents, "class", "svelte-1tqh76q");
			set_style(svelte_virtual_list_viewport, "height", /*height*/ ctx[0]);
			set_custom_element_data(svelte_virtual_list_viewport, "class", "svelte-1tqh76q");
			add_render_callback(() => /*svelte_virtual_list_viewport_elementresize_handler*/ ctx[17].call(svelte_virtual_list_viewport));
		},
		m(target, anchor) {
			insert(target, svelte_virtual_list_viewport, anchor);
			append(svelte_virtual_list_viewport, svelte_virtual_list_contents);

			for (let i = 0; i < each_blocks.length; i += 1) {
				each_blocks[i].m(svelte_virtual_list_contents, null);
			}

			/*svelte_virtual_list_contents_binding*/ ctx[15](svelte_virtual_list_contents);
			/*svelte_virtual_list_viewport_binding*/ ctx[16](svelte_virtual_list_viewport);
			svelte_virtual_list_viewport_resize_listener = add_resize_listener(svelte_virtual_list_viewport, /*svelte_virtual_list_viewport_elementresize_handler*/ ctx[17].bind(svelte_virtual_list_viewport));
			current = true;

			if (!mounted) {
				dispose = listen(svelte_virtual_list_viewport, "scroll", /*handle_scroll*/ ctx[7]);
				mounted = true;
			}
		},
		p(ctx, [dirty]) {
			if (dirty & /*$$scope, visible*/ 8208) {
				each_value = /*visible*/ ctx[4];
				group_outros();
				each_blocks = update_keyed_each(each_blocks, dirty, get_key, 1, ctx, each_value, each_1_lookup, svelte_virtual_list_contents, outro_and_destroy_block, create_each_block$1, null, get_each_context$1);
				check_outros();
			}

			if (!current || dirty & /*top*/ 32) {
				set_style(svelte_virtual_list_contents, "padding-top", /*top*/ ctx[5] + "px");
			}

			if (!current || dirty & /*bottom*/ 64) {
				set_style(svelte_virtual_list_contents, "padding-bottom", /*bottom*/ ctx[6] + "px");
			}

			if (!current || dirty & /*height*/ 1) {
				set_style(svelte_virtual_list_viewport, "height", /*height*/ ctx[0]);
			}
		},
		i(local) {
			if (current) return;

			for (let i = 0; i < each_value.length; i += 1) {
				transition_in(each_blocks[i]);
			}

			current = true;
		},
		o(local) {
			for (let i = 0; i < each_blocks.length; i += 1) {
				transition_out(each_blocks[i]);
			}

			current = false;
		},
		d(detaching) {
			if (detaching) detach(svelte_virtual_list_viewport);

			for (let i = 0; i < each_blocks.length; i += 1) {
				each_blocks[i].d();
			}

			/*svelte_virtual_list_contents_binding*/ ctx[15](null);
			/*svelte_virtual_list_viewport_binding*/ ctx[16](null);
			svelte_virtual_list_viewport_resize_listener();
			mounted = false;
			dispose();
		}
	};
}

function instance$2($$self, $$props, $$invalidate) {
	let { $$slots: slots = {}, $$scope } = $$props;
	let { items } = $$props;
	let { height = "100%" } = $$props;
	let { itemHeight = undefined } = $$props;
	let { start = 0 } = $$props;
	let { end = 0 } = $$props;

	// local state
	let height_map = [];

	let rows;
	let viewport;
	let contents;
	let viewport_height = 0;
	let visible;
	let mounted;
	let top = 0;
	let bottom = 0;
	let average_height;

	async function refresh(items, viewport_height, itemHeight) {
		const { scrollTop } = viewport;
		await tick(); // wait until the DOM is up to date
		let content_height = top - scrollTop;
		let i = start;

		while (content_height < viewport_height && i < items.length) {
			let row = rows[i - start];

			if (!row) {
				$$invalidate(9, end = i + 1);
				await tick(); // render the newly visible row
				row = rows[i - start];
			}

			const row_height = height_map[i] = itemHeight || row.offsetHeight;
			content_height += row_height;
			i += 1;
		}

		$$invalidate(9, end = i);
		const remaining = items.length - end;
		average_height = (top + content_height) / end;
		$$invalidate(6, bottom = remaining * average_height);
		height_map.length = items.length;
	}

	async function handle_scroll() {
		const { scrollTop } = viewport;
		const old_start = start;

		for (let v = 0; v < rows.length; v += 1) {
			height_map[start + v] = itemHeight || rows[v].offsetHeight;
		}

		let i = 0;
		let y = 0;

		while (i < items.length) {
			const row_height = height_map[i] || average_height;

			if (y + row_height > scrollTop) {
				$$invalidate(8, start = i);
				$$invalidate(5, top = y);
				break;
			}

			y += row_height;
			i += 1;
		}

		while (i < items.length) {
			y += height_map[i] || average_height;
			i += 1;
			if (y > scrollTop + viewport_height) break;
		}

		$$invalidate(9, end = i);
		const remaining = items.length - end;
		average_height = y / end;
		while (i < items.length) height_map[i++] = average_height;
		$$invalidate(6, bottom = remaining * average_height);

		// prevent jumping if we scrolled up into unknown territory
		if (start < old_start) {
			await tick();
			let expected_height = 0;
			let actual_height = 0;

			for (let i = start; i < old_start; i += 1) {
				if (rows[i - start]) {
					expected_height += height_map[i];
					actual_height += itemHeight || rows[i - start].offsetHeight;
				}
			}

			const d = actual_height - expected_height;
			viewport.scrollTo(0, scrollTop + d);
		}
	} // TODO if we overestimated the space these
	// rows would occupy we may need to add some

	// more. maybe we can just call handle_scroll again?
	// trigger initial refresh
	onMount(() => {
		rows = contents.getElementsByTagName("svelte-virtual-list-row");
		$$invalidate(12, mounted = true);
	});

	function svelte_virtual_list_contents_binding($$value) {
		binding_callbacks[$$value ? "unshift" : "push"](() => {
			contents = $$value;
			$$invalidate(3, contents);
		});
	}

	function svelte_virtual_list_viewport_binding($$value) {
		binding_callbacks[$$value ? "unshift" : "push"](() => {
			viewport = $$value;
			$$invalidate(2, viewport);
		});
	}

	function svelte_virtual_list_viewport_elementresize_handler() {
		viewport_height = this.offsetHeight;
		$$invalidate(1, viewport_height);
	}

	$$self.$$set = $$props => {
		if ("items" in $$props) $$invalidate(10, items = $$props.items);
		if ("height" in $$props) $$invalidate(0, height = $$props.height);
		if ("itemHeight" in $$props) $$invalidate(11, itemHeight = $$props.itemHeight);
		if ("start" in $$props) $$invalidate(8, start = $$props.start);
		if ("end" in $$props) $$invalidate(9, end = $$props.end);
		if ("$$scope" in $$props) $$invalidate(13, $$scope = $$props.$$scope);
	};

	$$self.$$.update = () => {
		if ($$self.$$.dirty & /*items, start, end*/ 1792) {
			$$invalidate(4, visible = items.slice(start, end).map((data, i) => {
				return { index: i + start, data };
			}));
		}

		if ($$self.$$.dirty & /*mounted, items, viewport_height, itemHeight*/ 7170) {
			// whenever `items` changes, invalidate the current heightmap
			if (mounted) refresh(items, viewport_height, itemHeight);
		}
	};

	return [
		height,
		viewport_height,
		viewport,
		contents,
		visible,
		top,
		bottom,
		handle_scroll,
		start,
		end,
		items,
		itemHeight,
		mounted,
		$$scope,
		slots,
		svelte_virtual_list_contents_binding,
		svelte_virtual_list_viewport_binding,
		svelte_virtual_list_viewport_elementresize_handler
	];
}

class VirtualList extends SvelteComponent {
	constructor(options) {
		super();
		if (!document.getElementById("svelte-1tqh76q-style")) add_css$2();

		init(this, options, instance$2, create_fragment$2, safe_not_equal, {
			items: 10,
			height: 0,
			itemHeight: 11,
			start: 8,
			end: 9
		});
	}
}

function enumKeys(obj) {
    return Object.keys(obj).filter((k) => Number.isNaN(+k));
}
function getBaseLog(x, y) {
    return Math.log(y) / Math.log(x);
}
function numDigits(x, base = 10) {
    return Math.max(Math.floor(getBaseLog(base, Math.abs(x))), 0) + 1;
}
function* iter_range(begin, end, step) {
    step = step ? step : 1;
    if (typeof end === "undefined") {
        end = begin > 0 ? begin : 0;
        begin = begin < 0 ? begin : 0;
    }
    if (begin == end) {
        return;
    }
    if (begin > end) {
        step = step * -1;
    }
    for (let x = begin; x < end; x += step) {
        yield x;
    }
}
function range(begin, end, step) {
    return Array.from(iter_range(begin, end, step));
}

/* src/Glyph.svelte generated by Svelte v3.38.3 */

function add_css$1() {
	var style = element("style");
	style.id = "svelte-1miow1p-style";
	style.textContent = "span.svelte-1miow1p.svelte-1miow1p{display:inline-block;background-color:var(--color);min-width:1ch;min-height:1em;padding:0 4px}main.selected.svelte-1miow1p span.svelte-1miow1p{box-shadow:inset 0px 0px 0px 1px red}main.svelte-1miow1p span.svelte-1miow1p:focus{background-color:wheat;outline:none}span.empty.svelte-1miow1p.svelte-1miow1p{color:#aaa}span.ascii.svelte-1miow1p.svelte-1miow1p{margin-left:0.2ch;padding:0 1px}span.number.svelte-1miow1p.svelte-1miow1p::before{content:attr(data-digits);display:inline;color:#aaa}";
	append(document.head, style);
}

// (18:2) {:else}
function create_else_block(ctx) {
	let span;
	let t_value = /*value*/ ctx[1].toString(/*type*/ ctx[2]).toUpperCase() + "";
	let t;
	let span_data_digits_value;

	return {
		c() {
			span = element("span");
			t = text(t_value);
			attr(span, "class", "number svelte-1miow1p");
			attr(span, "tabindex", "0");
			attr(span, "data-position", /*position*/ ctx[0]);
			attr(span, "data-digits", span_data_digits_value = ("0").repeat(/*digits*/ ctx[4]));
		},
		m(target, anchor) {
			insert(target, span, anchor);
			append(span, t);
		},
		p(ctx, dirty) {
			if (dirty & /*value, type*/ 6 && t_value !== (t_value = /*value*/ ctx[1].toString(/*type*/ ctx[2]).toUpperCase() + "")) set_data(t, t_value);

			if (dirty & /*position*/ 1) {
				attr(span, "data-position", /*position*/ ctx[0]);
			}

			if (dirty & /*digits*/ 16 && span_data_digits_value !== (span_data_digits_value = ("0").repeat(/*digits*/ ctx[4]))) {
				attr(span, "data-digits", span_data_digits_value);
			}
		},
		d(detaching) {
			if (detaching) detach(span);
		}
	};
}

// (14:23) 
function create_if_block_1$1(ctx) {
	let span;
	let t_value = String.fromCharCode(/*value*/ ctx[1]) + "";
	let t;

	return {
		c() {
			span = element("span");
			t = text(t_value);
			attr(span, "class", "ascii svelte-1miow1p");
			attr(span, "tabindex", "0");
			attr(span, "data-position", /*position*/ ctx[0]);
		},
		m(target, anchor) {
			insert(target, span, anchor);
			append(span, t);
		},
		p(ctx, dirty) {
			if (dirty & /*value*/ 2 && t_value !== (t_value = String.fromCharCode(/*value*/ ctx[1]) + "")) set_data(t, t_value);

			if (dirty & /*position*/ 1) {
				attr(span, "data-position", /*position*/ ctx[0]);
			}
		},
		d(detaching) {
			if (detaching) detach(span);
		}
	};
}

// (12:2) {#if value === undefined}
function create_if_block$1(ctx) {
	let span;
	let t_value = (".").repeat(/*digits*/ ctx[4] + 1) + "";
	let t;

	return {
		c() {
			span = element("span");
			t = text(t_value);
			attr(span, "class", "empty svelte-1miow1p");
		},
		m(target, anchor) {
			insert(target, span, anchor);
			append(span, t);
		},
		p(ctx, dirty) {
			if (dirty & /*digits*/ 16 && t_value !== (t_value = (".").repeat(/*digits*/ ctx[4] + 1) + "")) set_data(t, t_value);
		},
		d(detaching) {
			if (detaching) detach(span);
		}
	};
}

function create_fragment$1(ctx) {
	let main;

	function select_block_type(ctx, dirty) {
		if (/*value*/ ctx[1] === undefined) return create_if_block$1;
		if (/*type*/ ctx[2] === 0) return create_if_block_1$1;
		return create_else_block;
	}

	let current_block_type = select_block_type(ctx);
	let if_block = current_block_type(ctx);

	return {
		c() {
			main = element("main");
			if_block.c();
			attr(main, "class", "svelte-1miow1p");
			toggle_class(main, "selected", /*selected*/ ctx[3]);
		},
		m(target, anchor) {
			insert(target, main, anchor);
			if_block.m(main, null);
		},
		p(ctx, [dirty]) {
			if (current_block_type === (current_block_type = select_block_type(ctx)) && if_block) {
				if_block.p(ctx, dirty);
			} else {
				if_block.d(1);
				if_block = current_block_type(ctx);

				if (if_block) {
					if_block.c();
					if_block.m(main, null);
				}
			}

			if (dirty & /*selected*/ 8) {
				toggle_class(main, "selected", /*selected*/ ctx[3]);
			}
		},
		i: noop,
		o: noop,
		d(detaching) {
			if (detaching) detach(main);
			if_block.d();
		}
	};
}

function instance$1($$self, $$props, $$invalidate) {
	let digits;
	let { position = "" } = $$props;
	let { value } = $$props;
	let { type } = $$props;
	let { selected = false } = $$props;
	let { maxItems = 0 } = $$props;

	$$self.$$set = $$props => {
		if ("position" in $$props) $$invalidate(0, position = $$props.position);
		if ("value" in $$props) $$invalidate(1, value = $$props.value);
		if ("type" in $$props) $$invalidate(2, type = $$props.type);
		if ("selected" in $$props) $$invalidate(3, selected = $$props.selected);
		if ("maxItems" in $$props) $$invalidate(5, maxItems = $$props.maxItems);
	};

	$$self.$$.update = () => {
		if ($$self.$$.dirty & /*type, maxItems, value*/ 38) {
			$$invalidate(4, digits = Math.max(0, Math.ceil(getBaseLog(type, maxItems)) - (value !== null && value !== void 0 ? value : 0).toString(type || 2).length, Math.ceil(getBaseLog(type, 256)) - (value !== null && value !== void 0 ? value : 0).toString(type || 2).length));
		}
	};

	return [position, value, type, selected, digits, maxItems];
}

class Glyph extends SvelteComponent {
	constructor(options) {
		super();
		if (!document.getElementById("svelte-1miow1p-style")) add_css$1();

		init(this, options, instance$1, create_fragment$1, safe_not_equal, {
			position: 0,
			value: 1,
			type: 2,
			selected: 3,
			maxItems: 5
		});
	}
}

var NumberBase;
(function (NumberBase) {
    NumberBase[NumberBase["Binary"] = 2] = "Binary";
    NumberBase[NumberBase["Octal"] = 8] = "Octal";
    NumberBase[NumberBase["Decimal"] = 10] = "Decimal";
    NumberBase[NumberBase["Hexadecimal"] = 16] = "Hexadecimal";
})(NumberBase || (NumberBase = {}));

/* src/HexEditor.svelte generated by Svelte v3.38.3 */

function add_css() {
	var style = element("style");
	style.id = "svelte-1qk31u8-style";
	style.textContent = "main.svelte-1qk31u8.svelte-1qk31u8{height:var(--height);min-height:96px;width:var(--width);box-sizing:content-box;display:inline-flex;flex-direction:column;font-family:monospace;font-variant-numeric:slashed-zero;border:1px solid gray;user-select:none;-webkit-user-select:none;cursor:pointer}main.svelte-1qk31u8>header.svelte-1qk31u8{display:flex;box-shadow:0px 1px 0 rgba(0, 0, 0, 0.2), 0px 1px 4px rgba(0, 0, 0, 0.2)}main.svelte-1qk31u8>header .header-offset.svelte-1qk31u8{background-color:rgba(0, 0, 0, 0.1);min-width:110px;text-align:center}main.svelte-1qk31u8>header .header-data.svelte-1qk31u8{margin-left:20px}svelte-virtual-list-viewport{flex-grow:1}main.svelte-1qk31u8>footer.svelte-1qk31u8{background-color:rgba(0, 0, 0, 0.08);box-shadow:0px -1px 0 rgba(0, 0, 0, 0.2), 0px -1px 4px rgba(0, 0, 0, 0.2);padding:2px 1em;display:flex;font-size:12px;justify-content:center}main.svelte-1qk31u8 .hex-row.svelte-1qk31u8{display:flex;flex-wrap:nowrap}main.svelte-1qk31u8 .hex-row-offset.svelte-1qk31u8{background-color:rgba(0, 0, 0, 0.1);min-width:100px;padding-right:10px;margin-right:2em;justify-content:flex-end;display:flex;flex-wrap:nowrap}main.svelte-1qk31u8 .hex-row-data.svelte-1qk31u8{margin-right:1em;display:flex;flex-wrap:nowrap}main.svelte-1qk31u8 .hex-row-ascii.svelte-1qk31u8{margin:0 1em;display:flex;flex-wrap:nowrap}";
	append(document.head, style);
}

function get_each_context(ctx, list, i) {
	const child_ctx = ctx.slice();
	child_ctx[25] = list[i];
	return child_ctx;
}

function get_each_context_1(ctx, list, i) {
	const child_ctx = ctx.slice();
	child_ctx[25] = list[i];
	return child_ctx;
}

function get_each_context_2(ctx, list, i) {
	const child_ctx = ctx.slice();
	child_ctx[24] = list[i];
	return child_ctx;
}

function get_each_context_3(ctx, list, i) {
	const child_ctx = ctx.slice();
	child_ctx[24] = list[i];
	return child_ctx;
}

function get_each_context_4(ctx, list, i) {
	const child_ctx = ctx.slice();
	child_ctx[24] = list[i];
	return child_ctx;
}

// (44:2) {#if showHeader}
function create_if_block_1(ctx) {
	let header;
	let div0;
	let select0;
	let t0;
	let div1;
	let select1;
	let t1;
	let select2;
	let t2;
	let div2;
	let mounted;
	let dispose;
	let each_value_4 = /*numberBases*/ ctx[12];
	let each_blocks_2 = [];

	for (let i = 0; i < each_value_4.length; i += 1) {
		each_blocks_2[i] = create_each_block_4(get_each_context_4(ctx, each_value_4, i));
	}

	let each_value_3 = /*numberBases*/ ctx[12];
	let each_blocks_1 = [];

	for (let i = 0; i < each_value_3.length; i += 1) {
		each_blocks_1[i] = create_each_block_3(get_each_context_3(ctx, each_value_3, i));
	}

	let each_value_2 = [1, 2, 4, 8, 16];
	let each_blocks = [];

	for (let i = 0; i < 5; i += 1) {
		each_blocks[i] = create_each_block_2(get_each_context_2(ctx, each_value_2, i));
	}

	return {
		c() {
			header = element("header");
			div0 = element("div");
			select0 = element("select");

			for (let i = 0; i < each_blocks_2.length; i += 1) {
				each_blocks_2[i].c();
			}

			t0 = space();
			div1 = element("div");
			select1 = element("select");

			for (let i = 0; i < each_blocks_1.length; i += 1) {
				each_blocks_1[i].c();
			}

			t1 = space();
			select2 = element("select");

			for (let i = 0; i < 5; i += 1) {
				each_blocks[i].c();
			}

			t2 = space();
			div2 = element("div");
			if (/*offsetBase*/ ctx[1] === void 0) add_render_callback(() => /*select0_change_handler*/ ctx[19].call(select0));
			attr(div0, "class", "header-offset svelte-1qk31u8");
			set_style(div0, "--offsetWidth", /*offsetWidth*/ ctx[14]);
			if (/*dataBase*/ ctx[2] === void 0) add_render_callback(() => /*select1_change_handler*/ ctx[20].call(select1));
			attr(select2, "title", "Bytes per line");
			if (/*bytesPerLine*/ ctx[0] === void 0) add_render_callback(() => /*select2_change_handler*/ ctx[21].call(select2));
			attr(div1, "class", "header-data svelte-1qk31u8");
			set_style(div1, "--width", /*dataWidth*/ ctx[15]);
			attr(div2, "class", "header-ascii");
			set_style(div2, "--width", /*dataWidth*/ ctx[15]);
			attr(header, "class", "svelte-1qk31u8");
		},
		m(target, anchor) {
			insert(target, header, anchor);
			append(header, div0);
			append(div0, select0);

			for (let i = 0; i < each_blocks_2.length; i += 1) {
				each_blocks_2[i].m(select0, null);
			}

			select_option(select0, /*offsetBase*/ ctx[1]);
			append(header, t0);
			append(header, div1);
			append(div1, select1);

			for (let i = 0; i < each_blocks_1.length; i += 1) {
				each_blocks_1[i].m(select1, null);
			}

			select_option(select1, /*dataBase*/ ctx[2]);
			append(div1, t1);
			append(div1, select2);

			for (let i = 0; i < 5; i += 1) {
				each_blocks[i].m(select2, null);
			}

			select_option(select2, /*bytesPerLine*/ ctx[0]);
			append(header, t2);
			append(header, div2);

			if (!mounted) {
				dispose = [
					listen(select0, "change", /*select0_change_handler*/ ctx[19]),
					listen(select1, "change", /*select1_change_handler*/ ctx[20]),
					listen(select2, "change", /*select2_change_handler*/ ctx[21])
				];

				mounted = true;
			}
		},
		p(ctx, dirty) {
			if (dirty[0] & /*numberBases*/ 4096) {
				each_value_4 = /*numberBases*/ ctx[12];
				let i;

				for (i = 0; i < each_value_4.length; i += 1) {
					const child_ctx = get_each_context_4(ctx, each_value_4, i);

					if (each_blocks_2[i]) {
						each_blocks_2[i].p(child_ctx, dirty);
					} else {
						each_blocks_2[i] = create_each_block_4(child_ctx);
						each_blocks_2[i].c();
						each_blocks_2[i].m(select0, null);
					}
				}

				for (; i < each_blocks_2.length; i += 1) {
					each_blocks_2[i].d(1);
				}

				each_blocks_2.length = each_value_4.length;
			}

			if (dirty[0] & /*offsetBase, numberBases*/ 4098) {
				select_option(select0, /*offsetBase*/ ctx[1]);
			}

			if (dirty[0] & /*numberBases*/ 4096) {
				each_value_3 = /*numberBases*/ ctx[12];
				let i;

				for (i = 0; i < each_value_3.length; i += 1) {
					const child_ctx = get_each_context_3(ctx, each_value_3, i);

					if (each_blocks_1[i]) {
						each_blocks_1[i].p(child_ctx, dirty);
					} else {
						each_blocks_1[i] = create_each_block_3(child_ctx);
						each_blocks_1[i].c();
						each_blocks_1[i].m(select1, null);
					}
				}

				for (; i < each_blocks_1.length; i += 1) {
					each_blocks_1[i].d(1);
				}

				each_blocks_1.length = each_value_3.length;
			}

			if (dirty[0] & /*dataBase, numberBases*/ 4100) {
				select_option(select1, /*dataBase*/ ctx[2]);
			}

			if (dirty[0] & /*bytesPerLine*/ 1) {
				select_option(select2, /*bytesPerLine*/ ctx[0]);
			}
		},
		d(detaching) {
			if (detaching) detach(header);
			destroy_each(each_blocks_2, detaching);
			destroy_each(each_blocks_1, detaching);
			destroy_each(each_blocks, detaching);
			mounted = false;
			run_all(dispose);
		}
	};
}

// (48:10) {#each numberBases as item}
function create_each_block_4(ctx) {
	let option;
	let t0_value = NumberBase[/*item*/ ctx[24]] + "";
	let t0;
	let t1;
	let option_value_value;

	return {
		c() {
			option = element("option");
			t0 = text(t0_value);
			t1 = space();
			option.__value = option_value_value = /*item*/ ctx[24];
			option.value = option.__value;
		},
		m(target, anchor) {
			insert(target, option, anchor);
			append(option, t0);
			append(option, t1);
		},
		p: noop,
		d(detaching) {
			if (detaching) detach(option);
		}
	};
}

// (57:10) {#each numberBases as item}
function create_each_block_3(ctx) {
	let option;
	let t0_value = NumberBase[/*item*/ ctx[24]] + "";
	let t0;
	let t1;
	let option_value_value;

	return {
		c() {
			option = element("option");
			t0 = text(t0_value);
			t1 = space();
			option.__value = option_value_value = /*item*/ ctx[24];
			option.value = option.__value;
		},
		m(target, anchor) {
			insert(target, option, anchor);
			append(option, t0);
			append(option, t1);
		},
		p: noop,
		d(detaching) {
			if (detaching) detach(option);
		}
	};
}

// (64:10) {#each [1, 2, 4, 8, 16] as item}
function create_each_block_2(ctx) {
	let option;
	let t0;
	let t1;
	let t2_value = (/*item*/ ctx[24] === 1 ? "Byte" : "Bytes") + "";
	let t2;
	let t3;
	let option_value_value;

	return {
		c() {
			option = element("option");
			t0 = text(/*item*/ ctx[24]);
			t1 = space();
			t2 = text(t2_value);
			t3 = space();
			option.__value = option_value_value = /*item*/ ctx[24];
			option.value = option.__value;
		},
		m(target, anchor) {
			insert(target, option, anchor);
			append(option, t0);
			append(option, t1);
			append(option, t2);
			append(option, t3);
		},
		p: noop,
		d(detaching) {
			if (detaching) detach(option);
		}
	};
}

// (86:8) {#each range(0, bytesPerLine, 1) as i}
function create_each_block_1(ctx) {
	let glyph;
	let current;

	glyph = new Glyph({
			props: {
				value: /*u8arr*/ ctx[13][/*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25]],
				type: /*dataBase*/ ctx[2],
				position: /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25],
				selected: +/*mouseOverPosition*/ ctx[10] === /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25]
			}
		});

	return {
		c() {
			create_component(glyph.$$.fragment);
		},
		m(target, anchor) {
			mount_component(glyph, target, anchor);
			current = true;
		},
		p(ctx, dirty) {
			const glyph_changes = {};
			if (dirty[0] & /*item, bytesPerLine*/ 16777217) glyph_changes.value = /*u8arr*/ ctx[13][/*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25]];
			if (dirty[0] & /*dataBase*/ 4) glyph_changes.type = /*dataBase*/ ctx[2];
			if (dirty[0] & /*item, bytesPerLine*/ 16777217) glyph_changes.position = /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25];
			if (dirty[0] & /*mouseOverPosition, item, bytesPerLine*/ 16778241) glyph_changes.selected = +/*mouseOverPosition*/ ctx[10] === /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25];
			glyph.$set(glyph_changes);
		},
		i(local) {
			if (current) return;
			transition_in(glyph.$$.fragment, local);
			current = true;
		},
		o(local) {
			transition_out(glyph.$$.fragment, local);
			current = false;
		},
		d(detaching) {
			destroy_component(glyph, detaching);
		}
	};
}

// (96:8) {#each range(0, bytesPerLine, 1) as i}
function create_each_block(ctx) {
	let glyph;
	let current;

	glyph = new Glyph({
			props: {
				value: /*u8arr*/ ctx[13][/*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25]],
				type: 0,
				position: /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25],
				selected: +/*mouseOverPosition*/ ctx[10] === /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25]
			}
		});

	return {
		c() {
			create_component(glyph.$$.fragment);
		},
		m(target, anchor) {
			mount_component(glyph, target, anchor);
			current = true;
		},
		p(ctx, dirty) {
			const glyph_changes = {};
			if (dirty[0] & /*item, bytesPerLine*/ 16777217) glyph_changes.value = /*u8arr*/ ctx[13][/*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25]];
			if (dirty[0] & /*item, bytesPerLine*/ 16777217) glyph_changes.position = /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25];
			if (dirty[0] & /*mouseOverPosition, item, bytesPerLine*/ 16778241) glyph_changes.selected = +/*mouseOverPosition*/ ctx[10] === /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0] + /*i*/ ctx[25];
			glyph.$set(glyph_changes);
		},
		i(local) {
			if (current) return;
			transition_in(glyph.$$.fragment, local);
			current = true;
		},
		o(local) {
			transition_out(glyph.$$.fragment, local);
			current = false;
		},
		d(detaching) {
			destroy_component(glyph, detaching);
		}
	};
}

// (76:2) <VirtualList {items} let:item {height} bind:start bind:end>
function create_default_slot(ctx) {
	let div3;
	let div0;
	let glyph;
	let t0;
	let div1;
	let t1;
	let div2;
	let current;

	glyph = new Glyph({
			props: {
				value: /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0],
				type: /*offsetBase*/ ctx[1],
				maxItems: /*items*/ ctx[11].length
			}
		});

	let each_value_1 = range(0, /*bytesPerLine*/ ctx[0], 1);
	let each_blocks_1 = [];

	for (let i = 0; i < each_value_1.length; i += 1) {
		each_blocks_1[i] = create_each_block_1(get_each_context_1(ctx, each_value_1, i));
	}

	const out = i => transition_out(each_blocks_1[i], 1, 1, () => {
		each_blocks_1[i] = null;
	});

	let each_value = range(0, /*bytesPerLine*/ ctx[0], 1);
	let each_blocks = [];

	for (let i = 0; i < each_value.length; i += 1) {
		each_blocks[i] = create_each_block(get_each_context(ctx, each_value, i));
	}

	const out_1 = i => transition_out(each_blocks[i], 1, 1, () => {
		each_blocks[i] = null;
	});

	return {
		c() {
			div3 = element("div");
			div0 = element("div");
			create_component(glyph.$$.fragment);
			t0 = space();
			div1 = element("div");

			for (let i = 0; i < each_blocks_1.length; i += 1) {
				each_blocks_1[i].c();
			}

			t1 = space();
			div2 = element("div");

			for (let i = 0; i < each_blocks.length; i += 1) {
				each_blocks[i].c();
			}

			attr(div0, "class", "hex-row-offset svelte-1qk31u8");
			set_style(div0, "--width", /*offsetWidth*/ ctx[14]);
			attr(div1, "class", "hex-row-data svelte-1qk31u8");
			set_style(div1, "--width", /*dataWidth*/ ctx[15]);
			attr(div2, "class", "hex-row-ascii svelte-1qk31u8");
			set_style(div2, "--width", /*dataWidth*/ ctx[15]);
			attr(div3, "class", "hex-row svelte-1qk31u8");
		},
		m(target, anchor) {
			insert(target, div3, anchor);
			append(div3, div0);
			mount_component(glyph, div0, null);
			append(div3, t0);
			append(div3, div1);

			for (let i = 0; i < each_blocks_1.length; i += 1) {
				each_blocks_1[i].m(div1, null);
			}

			append(div3, t1);
			append(div3, div2);

			for (let i = 0; i < each_blocks.length; i += 1) {
				each_blocks[i].m(div2, null);
			}

			current = true;
		},
		p(ctx, dirty) {
			const glyph_changes = {};
			if (dirty[0] & /*item, bytesPerLine*/ 16777217) glyph_changes.value = /*item*/ ctx[24] * /*bytesPerLine*/ ctx[0];
			if (dirty[0] & /*offsetBase*/ 2) glyph_changes.type = /*offsetBase*/ ctx[1];
			if (dirty[0] & /*items*/ 2048) glyph_changes.maxItems = /*items*/ ctx[11].length;
			glyph.$set(glyph_changes);

			if (dirty[0] & /*u8arr, item, bytesPerLine, dataBase, mouseOverPosition*/ 16786437) {
				each_value_1 = range(0, /*bytesPerLine*/ ctx[0], 1);
				let i;

				for (i = 0; i < each_value_1.length; i += 1) {
					const child_ctx = get_each_context_1(ctx, each_value_1, i);

					if (each_blocks_1[i]) {
						each_blocks_1[i].p(child_ctx, dirty);
						transition_in(each_blocks_1[i], 1);
					} else {
						each_blocks_1[i] = create_each_block_1(child_ctx);
						each_blocks_1[i].c();
						transition_in(each_blocks_1[i], 1);
						each_blocks_1[i].m(div1, null);
					}
				}

				group_outros();

				for (i = each_value_1.length; i < each_blocks_1.length; i += 1) {
					out(i);
				}

				check_outros();
			}

			if (dirty[0] & /*u8arr, item, bytesPerLine, mouseOverPosition*/ 16786433) {
				each_value = range(0, /*bytesPerLine*/ ctx[0], 1);
				let i;

				for (i = 0; i < each_value.length; i += 1) {
					const child_ctx = get_each_context(ctx, each_value, i);

					if (each_blocks[i]) {
						each_blocks[i].p(child_ctx, dirty);
						transition_in(each_blocks[i], 1);
					} else {
						each_blocks[i] = create_each_block(child_ctx);
						each_blocks[i].c();
						transition_in(each_blocks[i], 1);
						each_blocks[i].m(div2, null);
					}
				}

				group_outros();

				for (i = each_value.length; i < each_blocks.length; i += 1) {
					out_1(i);
				}

				check_outros();
			}
		},
		i(local) {
			if (current) return;
			transition_in(glyph.$$.fragment, local);

			for (let i = 0; i < each_value_1.length; i += 1) {
				transition_in(each_blocks_1[i]);
			}

			for (let i = 0; i < each_value.length; i += 1) {
				transition_in(each_blocks[i]);
			}

			current = true;
		},
		o(local) {
			transition_out(glyph.$$.fragment, local);
			each_blocks_1 = each_blocks_1.filter(Boolean);

			for (let i = 0; i < each_blocks_1.length; i += 1) {
				transition_out(each_blocks_1[i]);
			}

			each_blocks = each_blocks.filter(Boolean);

			for (let i = 0; i < each_blocks.length; i += 1) {
				transition_out(each_blocks[i]);
			}

			current = false;
		},
		d(detaching) {
			if (detaching) detach(div3);
			destroy_component(glyph);
			destroy_each(each_blocks_1, detaching);
			destroy_each(each_blocks, detaching);
		}
	};
}

// (108:2) {#if showFooter}
function create_if_block(ctx) {
	let footer;
	let t0;
	let glyph0;
	let t1;
	let glyph1;
	let t2;
	let glyph2;
	let current;

	glyph0 = new Glyph({
			props: {
				value: /*start*/ ctx[8] * /*bytesPerLine*/ ctx[0],
				type: /*offsetBase*/ ctx[1],
				maxItems: /*items*/ ctx[11].length
			}
		});

	glyph1 = new Glyph({
			props: {
				value: /*end*/ ctx[9] * /*bytesPerLine*/ ctx[0],
				type: /*offsetBase*/ ctx[1],
				maxItems: /*items*/ ctx[11].length
			}
		});

	glyph2 = new Glyph({
			props: {
				value: /*items*/ ctx[11].length * /*bytesPerLine*/ ctx[0],
				type: /*offsetBase*/ ctx[1],
				maxItems: /*items*/ ctx[11].length
			}
		});

	return {
		c() {
			footer = element("footer");
			t0 = text("Showing\n      ");
			create_component(glyph0.$$.fragment);
			t1 = text("\n      -\n      ");
			create_component(glyph1.$$.fragment);
			t2 = text("\n      of\n      ");
			create_component(glyph2.$$.fragment);
			attr(footer, "class", "svelte-1qk31u8");
		},
		m(target, anchor) {
			insert(target, footer, anchor);
			append(footer, t0);
			mount_component(glyph0, footer, null);
			append(footer, t1);
			mount_component(glyph1, footer, null);
			append(footer, t2);
			mount_component(glyph2, footer, null);
			current = true;
		},
		p(ctx, dirty) {
			const glyph0_changes = {};
			if (dirty[0] & /*start, bytesPerLine*/ 257) glyph0_changes.value = /*start*/ ctx[8] * /*bytesPerLine*/ ctx[0];
			if (dirty[0] & /*offsetBase*/ 2) glyph0_changes.type = /*offsetBase*/ ctx[1];
			if (dirty[0] & /*items*/ 2048) glyph0_changes.maxItems = /*items*/ ctx[11].length;
			glyph0.$set(glyph0_changes);
			const glyph1_changes = {};
			if (dirty[0] & /*end, bytesPerLine*/ 513) glyph1_changes.value = /*end*/ ctx[9] * /*bytesPerLine*/ ctx[0];
			if (dirty[0] & /*offsetBase*/ 2) glyph1_changes.type = /*offsetBase*/ ctx[1];
			if (dirty[0] & /*items*/ 2048) glyph1_changes.maxItems = /*items*/ ctx[11].length;
			glyph1.$set(glyph1_changes);
			const glyph2_changes = {};
			if (dirty[0] & /*items, bytesPerLine*/ 2049) glyph2_changes.value = /*items*/ ctx[11].length * /*bytesPerLine*/ ctx[0];
			if (dirty[0] & /*offsetBase*/ 2) glyph2_changes.type = /*offsetBase*/ ctx[1];
			if (dirty[0] & /*items*/ 2048) glyph2_changes.maxItems = /*items*/ ctx[11].length;
			glyph2.$set(glyph2_changes);
		},
		i(local) {
			if (current) return;
			transition_in(glyph0.$$.fragment, local);
			transition_in(glyph1.$$.fragment, local);
			transition_in(glyph2.$$.fragment, local);
			current = true;
		},
		o(local) {
			transition_out(glyph0.$$.fragment, local);
			transition_out(glyph1.$$.fragment, local);
			transition_out(glyph2.$$.fragment, local);
			current = false;
		},
		d(detaching) {
			if (detaching) detach(footer);
			destroy_component(glyph0);
			destroy_component(glyph1);
			destroy_component(glyph2);
		}
	};
}

function create_fragment(ctx) {
	let main;
	let t0;
	let virtuallist;
	let updating_start;
	let updating_end;
	let t1;
	let current;
	let mounted;
	let dispose;
	let if_block0 = /*showHeader*/ ctx[4] && create_if_block_1(ctx);

	function virtuallist_start_binding(value) {
		/*virtuallist_start_binding*/ ctx[22](value);
	}

	function virtuallist_end_binding(value) {
		/*virtuallist_end_binding*/ ctx[23](value);
	}

	let virtuallist_props = {
		items: /*items*/ ctx[11],
		height: /*height*/ ctx[6],
		$$slots: {
			default: [
				create_default_slot,
				({ item }) => ({ 24: item }),
				({ item }) => [item ? 16777216 : 0]
			]
		},
		$$scope: { ctx }
	};

	if (/*start*/ ctx[8] !== void 0) {
		virtuallist_props.start = /*start*/ ctx[8];
	}

	if (/*end*/ ctx[9] !== void 0) {
		virtuallist_props.end = /*end*/ ctx[9];
	}

	virtuallist = new VirtualList({ props: virtuallist_props });
	binding_callbacks.push(() => bind(virtuallist, "start", virtuallist_start_binding));
	binding_callbacks.push(() => bind(virtuallist, "end", virtuallist_end_binding));
	let if_block1 = /*showFooter*/ ctx[5] && create_if_block(ctx);

	return {
		c() {
			main = element("main");
			if (if_block0) if_block0.c();
			t0 = space();
			create_component(virtuallist.$$.fragment);
			t1 = space();
			if (if_block1) if_block1.c();
			set_style(main, "--width", /*width*/ ctx[7]);
			set_style(main, "--height", /*height*/ ctx[6]);
			attr(main, "class", "svelte-1qk31u8");
			toggle_class(main, "readonly", /*readonly*/ ctx[3]);
		},
		m(target, anchor) {
			insert(target, main, anchor);
			if (if_block0) if_block0.m(main, null);
			append(main, t0);
			mount_component(virtuallist, main, null);
			append(main, t1);
			if (if_block1) if_block1.m(main, null);
			current = true;

			if (!mounted) {
				dispose = [
					listen(main, "mouseover", /*handleMouseOver*/ ctx[16]),
					listen(main, "mouseout", /*handleMouseOut*/ ctx[17])
				];

				mounted = true;
			}
		},
		p(ctx, dirty) {
			if (/*showHeader*/ ctx[4]) {
				if (if_block0) {
					if_block0.p(ctx, dirty);
				} else {
					if_block0 = create_if_block_1(ctx);
					if_block0.c();
					if_block0.m(main, t0);
				}
			} else if (if_block0) {
				if_block0.d(1);
				if_block0 = null;
			}

			const virtuallist_changes = {};
			if (dirty[0] & /*items*/ 2048) virtuallist_changes.items = /*items*/ ctx[11];
			if (dirty[0] & /*height*/ 64) virtuallist_changes.height = /*height*/ ctx[6];

			if (dirty[0] & /*bytesPerLine, item, mouseOverPosition, dataBase, offsetBase, items*/ 16780295 | dirty[1] & /*$$scope*/ 32) {
				virtuallist_changes.$$scope = { dirty, ctx };
			}

			if (!updating_start && dirty[0] & /*start*/ 256) {
				updating_start = true;
				virtuallist_changes.start = /*start*/ ctx[8];
				add_flush_callback(() => updating_start = false);
			}

			if (!updating_end && dirty[0] & /*end*/ 512) {
				updating_end = true;
				virtuallist_changes.end = /*end*/ ctx[9];
				add_flush_callback(() => updating_end = false);
			}

			virtuallist.$set(virtuallist_changes);

			if (/*showFooter*/ ctx[5]) {
				if (if_block1) {
					if_block1.p(ctx, dirty);

					if (dirty[0] & /*showFooter*/ 32) {
						transition_in(if_block1, 1);
					}
				} else {
					if_block1 = create_if_block(ctx);
					if_block1.c();
					transition_in(if_block1, 1);
					if_block1.m(main, null);
				}
			} else if (if_block1) {
				group_outros();

				transition_out(if_block1, 1, 1, () => {
					if_block1 = null;
				});

				check_outros();
			}

			if (!current || dirty[0] & /*width*/ 128) {
				set_style(main, "--width", /*width*/ ctx[7]);
			}

			if (!current || dirty[0] & /*height*/ 64) {
				set_style(main, "--height", /*height*/ ctx[6]);
			}

			if (dirty[0] & /*readonly*/ 8) {
				toggle_class(main, "readonly", /*readonly*/ ctx[3]);
			}
		},
		i(local) {
			if (current) return;
			transition_in(virtuallist.$$.fragment, local);
			transition_in(if_block1);
			current = true;
		},
		o(local) {
			transition_out(virtuallist.$$.fragment, local);
			transition_out(if_block1);
			current = false;
		},
		d(detaching) {
			if (detaching) detach(main);
			if (if_block0) if_block0.d();
			destroy_component(virtuallist);
			if (if_block1) if_block1.d();
			mounted = false;
			run_all(dispose);
		}
	};
}

function instance($$self, $$props, $$invalidate) {
	let items;
	let { data = new ArrayBuffer(0) } = $$props;
	let { readonly = false } = $$props;
	let { showHeader = true } = $$props;
	let { showFooter = true } = $$props;
	let { height = "auto" } = $$props;
	let { width = "auto" } = $$props;
	let { offsetBase = NumberBase.Hexadecimal } = $$props;
	let { dataBase = NumberBase.Hexadecimal } = $$props;
	let { bytesPerLine = 8 } = $$props;
	let start = 0;
	let end = 0;
	const numberBases = enumKeys(NumberBase).map(item => NumberBase[item]);
	let mouseOverPosition = undefined;
	const u8arr = new Uint8Array(data);
	const offsetWidth = numDigits(u8arr.length);
	const dataWidth = bytesPerLine * numDigits(offsetBase);

	function handleMouseOver(event) {
		const position = event.target.dataset.position;

		if (position !== undefined && position !== "undefined") {
			$$invalidate(10, mouseOverPosition = position);
		}
	}

	function handleMouseOut(event) {
		const position = event.target.dataset.position;

		if ($$invalidate(10, mouseOverPosition = position)) {
			$$invalidate(10, mouseOverPosition = undefined);
		}
	}

	function select0_change_handler() {
		offsetBase = select_value(this);
		$$invalidate(1, offsetBase);
		$$invalidate(12, numberBases);
	}

	function select1_change_handler() {
		dataBase = select_value(this);
		$$invalidate(2, dataBase);
		$$invalidate(12, numberBases);
	}

	function select2_change_handler() {
		bytesPerLine = select_value(this);
		$$invalidate(0, bytesPerLine);
	}

	function virtuallist_start_binding(value) {
		start = value;
		$$invalidate(8, start);
	}

	function virtuallist_end_binding(value) {
		end = value;
		$$invalidate(9, end);
	}

	$$self.$$set = $$props => {
		if ("data" in $$props) $$invalidate(18, data = $$props.data);
		if ("readonly" in $$props) $$invalidate(3, readonly = $$props.readonly);
		if ("showHeader" in $$props) $$invalidate(4, showHeader = $$props.showHeader);
		if ("showFooter" in $$props) $$invalidate(5, showFooter = $$props.showFooter);
		if ("height" in $$props) $$invalidate(6, height = $$props.height);
		if ("width" in $$props) $$invalidate(7, width = $$props.width);
		if ("offsetBase" in $$props) $$invalidate(1, offsetBase = $$props.offsetBase);
		if ("dataBase" in $$props) $$invalidate(2, dataBase = $$props.dataBase);
		if ("bytesPerLine" in $$props) $$invalidate(0, bytesPerLine = $$props.bytesPerLine);
	};

	$$self.$$.update = () => {
		if ($$self.$$.dirty[0] & /*bytesPerLine*/ 1) {
			$$invalidate(11, items = [...Array(Math.max(4, Math.ceil(u8arr.length / bytesPerLine))).keys()]);
		}
	};

	return [
		bytesPerLine,
		offsetBase,
		dataBase,
		readonly,
		showHeader,
		showFooter,
		height,
		width,
		start,
		end,
		mouseOverPosition,
		items,
		numberBases,
		u8arr,
		offsetWidth,
		dataWidth,
		handleMouseOver,
		handleMouseOut,
		data,
		select0_change_handler,
		select1_change_handler,
		select2_change_handler,
		virtuallist_start_binding,
		virtuallist_end_binding
	];
}

class HexEditor extends SvelteComponent {
	constructor(options) {
		super();
		if (!document.getElementById("svelte-1qk31u8-style")) add_css();

		init(
			this,
			options,
			instance,
			create_fragment,
			safe_not_equal,
			{
				data: 18,
				readonly: 3,
				showHeader: 4,
				showFooter: 5,
				height: 6,
				width: 7,
				offsetBase: 1,
				dataBase: 2,
				bytesPerLine: 0
			},
			[-1, -1]
		);
	}
}
