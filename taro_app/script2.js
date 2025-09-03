// Функция для плавной прокрутки (оставляем без изменений)
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

        if (timeElapsed < duration) {
            requestAnimationFrame(animation);
        }
    }

    function easeInOutQuad(t) {
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }

    requestAnimationFrame(animation);
}

// Функция для получения оставшихся запросов
async function fetchRemainingRequests(userId) {
    try {
        const response = await fetch('https://ai-girls.ru/remaining-requests', {
            method: 'GET',
            headers: {
                'X-Telegram-User-Id': userId
            }
        });

        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        const data = await response.json();
        const remaining = data.remaining;
        document.getElementById("remaining-requests").innerText = `(осталось запросов: ${remaining})`;
    } catch (error) {
        console.error('Ошибка получения оставшихся запросов:', error);
        document.getElementById("remaining-requests").innerText = ``;
    }
}

// Функция для отправки запроса в YandexGPT (оставляем без изменений)
async function getYandexGPTResponse(question, selectedCards, userId) {
    try {
        const response = await fetch('https://ai-girls.ru/yandex-gpt', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': userId
            },
            body: JSON.stringify({ question, cards: selectedCards, user_id: userId })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || `Ошибка HTTP: ${response.status}`);
        }

        const data = await response.json();
        return data.response || 'Не удалось получить ответ.';
    } catch (error) {
        console.error('Ошибка прокси:', error);
        return error.message || 'Не удалось получить ответ. Проверьте подключение или повторите попытку.';
    }
}


// Функция для отображения надписи "Спасибо 😊"
function showThanksMessage() {
    const thanksMessage = document.getElementById("thanks-message");
    thanksMessage.style.display = "block";
    thanksMessage.style.opacity = "1";

    // Скрываем через 2 секунды
    setTimeout(() => {
        thanksMessage.style.opacity = "0";
        setTimeout(() => {
            thanksMessage.style.display = "none";
        }, 500); // Ждём завершения затухания
    }, 2000);
}

// Функция для проверки состояния кнопки
function updateButtonState() {
    const questionInput = document.getElementById("question").value;
    const startBtn = document.getElementById("start-btn");
    startBtn.disabled = !questionInput.trim();
}

document.getElementById("question").addEventListener("input", updateButtonState);
document.getElementById("thank-btn").addEventListener("click", showThanksMessage);

// Инициализация при загрузке страницы
document.addEventListener("DOMContentLoaded", () => {
    const user = window.Telegram.WebApp.initDataUnsafe.user || {};
    const userId = user.id || "unknown";
    fetchRemainingRequests(userId); // Получаем количество оставшихся запросов
});




// Функция для запуска расклада (добавляем обновление оставшихся запросов после выполнения)
// ... предыдущий код без изменений ...

// Функция для запуска расклада (с изменённым расположением карт)
async function startReading() {
    const questionInput = document.getElementById("question").value;
    const question = questionInput.trim() + "\nЭто расклад да/нет - то есть итоговый ответ должен быть либо да или нет.";

    const user = window.Telegram.WebApp.initDataUnsafe.user || {};
    const userId = user.id || "unknown";

    const answerDiv = document.getElementById("answer");
    answerDiv.style.display = "none";
    document.getElementById("answer-text").innerText = "";
    const thankBtn = document.getElementById("thank-btn");
    thankBtn.style.display = "none"; // Скрываем кнопку до ответа

    const animationDiv = document.getElementById("animation");
    animationDiv.innerHTML = ""; // Очищаем содержимое
    animationDiv.style.display = "flex"; // Используем flex для центрирования
    animationDiv.style.justifyContent = "center";
    animationDiv.style.alignItems = "center";
    animationDiv.style.height = "0px"; // Задаем высоту для контейнера

    // Выбираем 1 уникальную карту
    const selectedCards = [];
    while (selectedCards.length < 1) {
        const randomIndex = Math.floor(Math.random() * cards.length);
        const card = cards[randomIndex];
        if (!selectedCards.includes(card)) {
            selectedCards.push(card);
        }
    }
    const selectedCard = selectedCards[0];

    // Настраиваем размеры карты
    const screenWidth = window.innerWidth;
    const baseCardWidth = screenWidth < 600 ? screenWidth / 3 - 20 : 120;
    const cardHeight = baseCardWidth * 1.5;

    // Создаем элемент карты
    const cardElem = document.createElement("div");
    cardElem.classList.add("card");
    cardElem.style.width = `${baseCardWidth}px`;
    cardElem.style.height = `${cardHeight}px`;

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
    frontImg.src = `images/${selectedCard}.jpg`;
    frontImg.alt = selectedCard;
    cardFront.appendChild(frontImg);

    cardInner.appendChild(cardBack);
    cardInner.appendChild(cardFront);
    cardElem.appendChild(cardInner);

    // Добавляем карту в animationDiv
    animationDiv.appendChild(cardElem);

    // Запускаем запрос к YandexGPT заранее и сохраняем промис
    const gptPromise = getYandexGPTResponse(question, selectedCards, userId);

    // Переворачиваем карту через 1 секунду
    setTimeout(() => {
        cardElem.classList.add("flipped");
    }, 2000);

    answerDiv.style.display = "block";
    document.getElementById("answer-text").innerText = ``;
    smoothScrollTo(animationDiv, 2500);

    // Для ожидания
    const loadingDiv = document.getElementById("loading");
    
    // Показываем индикатор загрузки с меняющимися фразами через 2500 мс
    setTimeout(() => {
        loadingDiv.style.display = "block"; // Показываем индикатор после переворота карт

        // Массив фраз для смены
        const loadingMessages = [
            "Получаем ответ на ваш запрос...",
            "Анализируем выпавшие карты...",
            "Формируем предсказание...",
            "Смотрим в будущее для вас..."
        ];
        let messageIndex = 0;
        const loadingText = document.getElementById("loading-text");

        // Устанавливаем первую фразу сразу
        loadingText.innerText = loadingMessages[messageIndex];

        // Запускаем смену текста каждые 3 секунды
        const textInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % loadingMessages.length; // Циклический переход по массиву
            loadingText.innerText = loadingMessages[messageIndex];
        }, 3000);

        // Сохраняем textInterval в глобальной области видимости, чтобы можно было остановить его позже
        window.loadingTextInterval = textInterval;
    }, 2500);


    // Показываем ответ
    setTimeout(async () => {
        const gptResponse = await gptPromise;
        // Скрываем индикатор загрузки
        loadingDiv.style.display = "none";
        // Останавливаем смену текста, если интервал был запущен
        if (window.loadingTextInterval) {
            clearInterval(window.loadingTextInterval);
        }
        const formattedGptResponse = gptResponse.replace(/\n/g, "<br>");
        const boldedResponse = formattedGptResponse.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        const cleanedResponse = boldedResponse.replace(/\*/g, "");
        const cleanedResponse1 = cleanedResponse.replace(/#/g, "");

        const answerText = `
            <strong style="font-size: 20px;">Выпавшая карта:</strong><br><br>
            1) ${selectedCard}<br>
            <hr class="divider">
            <strong style="font-size: 20px;">Ответ на заданный вопрос с учетом выпавшей карты:</strong><br><br>
            ${cleanedResponse1}
        `;
        answerDiv.classList.add("show");
        document.getElementById("answer-text").innerHTML = answerText;
        thankBtn.style.display = "block"; // Показываем кнопку после ответа
        smoothScrollTo(answerDiv, 3000);

        // Обновляем количество оставшихся запросов
        fetchRemainingRequests(userId);
    }, 100);
}

document.getElementById("start-btn").addEventListener("click", startReading);

// Инициализация Telegram WebApp
if (typeof Telegram !== "undefined" && Telegram.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
}
