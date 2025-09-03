// Tarot Spread "Волна перемен" – 8 cards (3-2-3 grid)
// Adapted for single‑person inputs: имя, возраст, дополнительная информация

// --------------------- Общие утилиты (без изменений) ---------------------
function smoothScrollTo(target, duration = 1000) {
    const start = window.scrollY;
    let targetPosition;
    if (target instanceof HTMLElement) {
        targetPosition = target.getBoundingClientRect().top + start - 50;
    } else {
        targetPosition = document.documentElement.scrollHeight - window.innerHeight;
    }
    const distance = targetPosition - start;
    let startTime = null;
    function animation(currentTime) {
        if (startTime === null) startTime = currentTime;
        const timeElapsed = currentTime - startTime;
        const progress = Math.min(timeElapsed / duration, 1);
        const ease = easeInOutQuad(progress);
        window.scrollTo(0, start + distance * ease);
        if (timeElapsed < duration) requestAnimationFrame(animation);
    }
    function easeInOutQuad(t) {
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }
    requestAnimationFrame(animation);
}

async function fetchRemainingRequests(userId) {
    try {
        const response = await fetch("https://ai-girls.ru/remaining-requests", {
            method: "GET",
            headers: { "X-Telegram-User-Id": userId }
        });
        if (!response.ok) throw new Error(`Ошибка HTTP: ${response.status}`);
        const data = await response.json();
        document.getElementById("remaining-requests").innerText = `(осталось запросов: ${data.remaining})`;
    } catch (error) {
        console.error("Ошибка получения оставшихся запросов:", error);
        document.getElementById("remaining-requests").innerText = "";
    }
}

async function getYandexGPTResponse(question, selectedCards, userId) {
    try {
        const response = await fetch("https://ai-girls.ru/yandex-gpt", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Telegram-User-Id": userId
            },
            body: JSON.stringify({
                question,
                cards: selectedCards,
                user_id: userId,
                chat_id: chatId,
                source: "volna_peremen"
            })
        });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || `Ошибка HTTP: ${response.status}`);
        }
        const data = await response.json();
        return data.response || "Не удалось получить ответ.";
    } catch (error) {
        console.error("Ошибка прокси:", error);
        return (
            error.message || "Не удалось получить ответ. Проверьте подключение или повторите попытку."
        );
    }
}

function showThanksMessage() {
    const thanksMessage = document.getElementById("thanks-message");
    thanksMessage.style.display = "block";
    thanksMessage.style.opacity = "1";
    setTimeout(() => {
        thanksMessage.style.opacity = "0";
        setTimeout(() => (thanksMessage.style.display = "none"), 500);
    }, 2000);
}

function updateButtonState() {
    const nameValue = document.getElementById("name").value.trim();
    const ageValue = document.getElementById("age").value.trim();
    document.getElementById("start-btn").disabled = !(nameValue && ageValue);
}

document.getElementById("name").addEventListener("input", updateButtonState);
document.getElementById("age").addEventListener("input", updateButtonState);
document.getElementById("thank-btn").addEventListener("click", showThanksMessage);

document.addEventListener("DOMContentLoaded", () => {
    const user = window.Telegram.WebApp.initDataUnsafe.user || {};
    fetchRemainingRequests(user.id || "unknown");
});

// --------------------- NEW Spread: 8 cards (3-2-3) ---------------------
async function startReading() {
    const name = document.getElementById("name").value.trim();
    const age = document.getElementById("age").value.trim();
    const additionalInfo = document.getElementById("additional-info").value.trim();

    // Сбор вопроса для ЯндексGPT
    const question =
        `Расклад \"Волна перемен\" (8 карт)\n\n` +
        `Информация о кверенте:\nИмя: ${name}\nВозраст: ${age}\nДополнительная информация: ${additionalInfo || "—"}\n\n` +
        `Позиции карт:\n` +
        `1. Текущая ситуация – Что происходит в жизни кверента?\n` +
        `2. Причина перемен – Что вызвало эти изменения?\n` +
        `3. Страх или сопротивление – Что мешает принять перемены?\n` +
        `4. Скрытая возможность – Какой потенциал несут перемены?\n` +
        `5. Необходимое действие – Как адаптироваться к изменениям?\n` +
        `6. Поддержка окружения – Кто или что поможет в переходе?\n` +
        `7. Краткосрочный исход – Что произойдёт в ближайшем будущем?\n` +
        `8. Долгосрочный результат – Куда приведут эти перемены?\n\n` +
        `Ответ должен быть максимально развернутым. Количество слов в ответе не менее 1200.`;

    const user = window.Telegram.WebApp.initDataUnsafe.user || {};
    const userId = user.id || "unknown";

    // Сброс UI
    const answerDiv = document.getElementById("answer");
    answerDiv.style.display = "none";
    document.getElementById("answer-text").innerText = "";
    const thankBtn = document.getElementById("thank-btn");
    thankBtn.style.display = "none";

    const animationDiv = document.getElementById("animation");
    animationDiv.style.display = "block";
    animationDiv.innerHTML =
        '<div id="deck" class="deck"><img src="images/deck1.jpg" alt="Колода карт" style="width: 100%; height: 100%;"></div>';

    // Выбор 8 уникальных карт
    const selectedCards = [];
    while (selectedCards.length < 8) {
        const card = cards[Math.floor(Math.random() * cards.length)];
        if (!selectedCards.includes(card)) selectedCards.push(card);
    }

    // Отправляем вопрос к GPT заранее
    const gptPromise = getYandexGPTResponse(question, selectedCards, userId);

    // Геометрия раскладки: 3-2-3
    const screenWidth = window.innerWidth;
    const gap = 10;
    const baseCardWidth = screenWidth < 600 ? screenWidth / 3 - 20 : 120;
    const cardWidth = baseCardWidth + gap;
    const totalRowWidth3 = baseCardWidth * 3 + gap * 2;
    const totalRowWidth2 = baseCardWidth * 2 + gap;
    const startLeftRow3 = Math.max((screenWidth - totalRowWidth3) / 2, 10);
    const startLeftRow2 = Math.max((screenWidth - totalRowWidth2) / 2, 10);

    const deck = document.getElementById("deck");
    deck.style.width = `${baseCardWidth}px`;
    const deckHeight = baseCardWidth * 1.5;
    const deckTop = 50;

    // Позиции по строкам
    const rowTop = [
        deckTop + deckHeight + deckHeight / 2, // Первая строка (3 карты)
        deckTop + deckHeight + deckHeight / 2 + deckHeight + gap, // Вторая строка (2 карты)
        deckTop + deckHeight + deckHeight / 2 + (deckHeight + gap) * 2 // Третья строка (3 карты)
    ];

    const cardElements = [];
    const rowCardCounts = [3, 2, 3];
    let cardIndex = 0;

    rowCardCounts.forEach((count, row) => {
        const startLeft = count === 3 ? startLeftRow3 : startLeftRow2;
        for (let col = 0; col < count; col++) {
            const card = selectedCards[cardIndex];
            const cardElem = document.createElement("div");
            cardElem.classList.add("card");
            cardElem.style.width = `${baseCardWidth}px`;
            cardElem.style.height = `${deckHeight}px`;

            const cardInner = document.createElement("div");
            cardInner.classList.add("card-inner");

            const cardBack = document.createElement("div");
            cardBack.classList.add("card-back");
            const backImg = document.createElement("img");
            backImg.src = "images/deck1.jpg";
            backImg.alt = "Задняя сторона карты";
            cardBack.appendChild(backImg);

            const cardFront = document.createElement("div");
            cardFront.classList.add("card-front");
            const frontImg = document.createElement("img");
            frontImg.src = `images/${card}.jpg`;
            frontImg.alt = card;
            cardFront.appendChild(frontImg);

            cardInner.appendChild(cardBack);
            cardInner.appendChild(cardFront);
            cardElem.appendChild(cardInner);

            const leftPos = startLeft + col * cardWidth;
            const topPos = rowTop[row];

            cardElem.style.left = `${leftPos}px`;
            cardElem.style.top = `${topPos}px`;
            cardElem.style.animation = `spread-out 2s ease-in-out forwards ${cardIndex * 0.5}s`;

            animationDiv.appendChild(cardElem);
            cardElements.push(cardElem);
            cardIndex++;
        }
    });

    const lastSpreadOut = 2000 + (selectedCards.length - 1) * 500;
    cardElements.forEach((el, idx) => {
        setTimeout(() => el.classList.add("flipped"), lastSpreadOut + idx * 500);
    });

    answerDiv.style.display = "block";
    animationDiv.style.minHeight = `${rowTop[2] + deckHeight + 20}px`;
    smoothScrollTo(answerDiv, 6000);

    // ИНДИКАТОР загрузки через 10 секунд
    const loadingDiv = document.getElementById("loading");
    setTimeout(() => {
        loadingDiv.style.display = "block";
        const messages = [
            "Получаем ответ на ваш запрос...",
            "Анализируем текущую ситуацию и перемены...",
            "Формируем прорицание...",
            "Раскрываем перспективы изменений..."
        ];
        let i = 0;
        const loadingText = document.getElementById("loading-text");
        loadingText.innerText = messages[i];
        window.loadingTextInterval = setInterval(() => {
            i = (i + 1) % messages.length;
            loadingText.innerText = messages[i];
        }, 3000);
    }, 10000);

    // Получаем ответ GPT
    setTimeout(async () => {
        const gptResponse = await gptPromise;
        loadingDiv.style.display = "none";
        if (window.loadingTextInterval) clearInterval(window.loadingTextInterval);

        const htmlResponse = gptResponse
            .replace(/\n/g, "<br>")
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*/g, "")
            .replace(/#/g, "");

        const answerText =
            `<strong style="font-size: 20px;">Выпавшие карты:</strong><br><br>` +
            selectedCards.map((c, i) => `${i + 1}) ${c}`).join("<br>") +
            `<hr class="divider">` +
            `<strong style="font-size: 20px;">Ответ на расклад:</strong><br><br>` +
            htmlResponse;


        answerDiv.classList.add("show");
        document.getElementById("answer-text").innerHTML = answerText;
        thankBtn.style.display = "block";
        smoothScrollTo(answerDiv, 3000);
        fetchRemainingRequests(userId);
    }, 100);
}

document.getElementById("start-btn").addEventListener("click", startReading);

if (typeof Telegram !== "undefined" && Telegram.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
}