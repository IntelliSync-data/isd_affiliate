/* /my/affiliate: pick a source to see its link, copy it in one click. */
(function () {
    "use strict";

    function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text);
        }
        // http:// pages have no clipboard API: fall back to a selection
        const field = document.createElement("textarea");
        field.value = text;
        field.setAttribute("readonly", "");
        field.style.position = "fixed";
        field.style.opacity = "0";
        document.body.appendChild(field);
        field.select();
        document.execCommand("copy");
        document.body.removeChild(field);
        return Promise.resolve();
    }

    function setUp(box) {
        const select = box.querySelector(".o_isd_aff_source");
        const input = box.querySelector(".o_isd_aff_link");
        const button = box.querySelector(".o_isd_aff_copy");
        const icon = box.querySelector(".o_isd_aff_icon");
        if (!select || !input || !button) {
            return;
        }
        const label = button.textContent;
        select.addEventListener("change", () => {
            const option = select.options[select.selectedIndex];
            input.value = option.dataset.url || "";
            if (icon) {
                const src = option.dataset.icon || "";
                icon.classList.toggle("d-none", !src);
                if (src) {
                    icon.src = src;
                }
            }
            button.textContent = label;
        });
        button.addEventListener("click", () => {
            copyText(input.value).then(() => {
                button.textContent = button.dataset.copiedLabel || label;
                setTimeout(() => (button.textContent = label), 2000);
            });
        });
    }

    function init() {
        document.querySelectorAll(".o_isd_aff_links").forEach(setUp);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
