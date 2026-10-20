/* Provide touch-friendly navigation, a display-only timer, and retryable autosave. */
(function initializeMockExam() {
    "use strict";

    const examPage = document.getElementById("exam-page");
    const countdown = document.getElementById("exam-countdown");
    if (!examPage || !countdown) {
        return;
    }

    const questionPanels = Array.from(document.querySelectorAll(".question-panel"));
    const saveStatus = document.getElementById("answer-save-status");
    const pendingSaves = new Set();
    const unsavedForms = new Set();

    function showQuestion(index) {
        questionPanels.forEach((panel, panelIndex) => {
            panel.hidden = panelIndex !== index;
        });
    }

    document.querySelectorAll("[data-question-target]").forEach((button, index) => {
        button.addEventListener("click", () => showQuestion(index));
    });
    showQuestion(0);

    async function saveAnswer(form) {
        const csrfInput = form.querySelector("[name=csrfmiddlewaretoken]");
        const payload = new URLSearchParams(new FormData(form));
        saveStatus.textContent = "Saving answer…";
        try {
            const response = await fetch(form.action, {
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRFToken": csrfInput.value, "Content-Type": "application/x-www-form-urlencoded" },
                body: payload,
            });
            const result = await response.json();
            if (!response.ok) {
                saveStatus.textContent = result.error || "Answer could not be saved.";
                if (response.status === 409) {
                    window.location.assign(examPage.dataset.attemptUrl);
                }
                return false;
            }
            unsavedForms.delete(form);
            saveStatus.textContent = "Answer saved.";
            return true;
        } catch (error) {
            saveStatus.textContent = "Connection interrupted. Change or save the answer again to retry.";
            return false;
        }
    }

    function queueSave(form) {
        // Serialize saves per attempt page so slower earlier requests cannot overwrite newer choices.
        unsavedForms.add(form);
        const save = Array.from(pendingSaves).reduce((prior, pending) => prior.then(() => pending), Promise.resolve())
            .then(() => saveAnswer(form));
        pendingSaves.add(save);
        save.finally(() => pendingSaves.delete(save));
        return save;
    }

    document.querySelectorAll(".answer-form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            queueSave(form);
        });
        form.querySelectorAll("input[type=radio]").forEach((input) => {
            input.addEventListener("change", () => form.requestSubmit());
        });
        form.querySelector(".clear-answer").addEventListener("click", () => {
            form.querySelectorAll("input[type=radio]").forEach((input) => { input.checked = false; });
            queueSave(form);
        });
    });

    document.getElementById("submit-attempt-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!window.confirm("Submit this examination now? You cannot change answers after submission.")) {
            return;
        }
        const submitForm = event.currentTarget;
        const submitButton = submitForm.querySelector("button[type=submit]");
        submitButton.disabled = true;
        let saveFailed = false;
        while (pendingSaves.size > 0 || unsavedForms.size > 0) {
            Array.from(unsavedForms).forEach((form) => queueSave(form));
            const saveOutcomes = await Promise.all(Array.from(pendingSaves));
            if (saveOutcomes.some((wasSaved) => !wasSaved)) {
                saveFailed = true;
                break;
            }
        }
        if (saveFailed || unsavedForms.size > 0) {
            submitButton.disabled = false;
            saveStatus.textContent = "An answer was not saved. Retry the save before submitting.";
            return;
        }
        document.querySelectorAll(".answer-form input, .answer-form button").forEach((control) => { control.disabled = true; });
        HTMLFormElement.prototype.submit.call(submitForm);
    });

    const serverOffsetMs = Date.parse(countdown.dataset.serverNow) - Date.now();
    const deadline = Date.parse(countdown.dataset.deadline);
    function updateCountdown() {
        const serverNow = Date.now() + serverOffsetMs;
        const remainingSeconds = Math.max(0, Math.ceil((deadline - serverNow) / 1000));
        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = remainingSeconds % 60;
        countdown.textContent = `${minutes}:${String(seconds).padStart(2, "0")} remaining`;
        if (remainingSeconds === 0) {
            countdown.textContent = "Checking server deadline…";
            window.location.assign(examPage.dataset.attemptUrl);
            return;
        }
        window.setTimeout(updateCountdown, 1000);
    }
    updateCountdown();
}());
