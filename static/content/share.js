/* Progressive enhancement for native sharing and accessible copy-link controls. */
(() => {
    const controlGroups = document.querySelectorAll("[data-share-controls]");

    controlGroups.forEach((group) => {
        const shareButton = group.querySelector("[data-share-page]");
        const copyButton = group.querySelector("[data-copy-page-link]");
        const status = group.querySelector("[data-share-status]");
        const shareData = {
            title: group.dataset.shareTitle,
            url: group.dataset.shareUrl,
        };

        group.hidden = false;

        if (!navigator.share) {
            shareButton.hidden = true;
        }

        shareButton.addEventListener("click", async () => {
            try {
                await navigator.share(shareData);
            } catch (error) {
                if (error.name !== "AbortError") {
                    status.textContent = group.dataset.shareError;
                }
            }
        });

        copyButton.addEventListener("click", async () => {
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(shareData.url);
                } else {
                    const temporaryInput = document.createElement("textarea");
                    temporaryInput.value = shareData.url;
                    temporaryInput.setAttribute("readonly", "");
                    temporaryInput.className = "visually-hidden";
                    document.body.appendChild(temporaryInput);
                    temporaryInput.select();
                    const copied = document.execCommand("copy");
                    temporaryInput.remove();
                    if (!copied) {
                        throw new Error("Copy command failed");
                    }
                }
                status.textContent = group.dataset.copySuccess;
            } catch (error) {
                status.textContent = group.dataset.copyFailed;
            }
        });
    });
})();
