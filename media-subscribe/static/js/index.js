var currentPage = 1; // 当前页码
var itemsPerPage = 10; // 每页显示的项目数

const statusMap = {
    'PENDING': '待处理',
    'WAITING': '等待下载',
    'UNSUPPORTED': '不支持',
    'DOWNLOADING': '下载中',
    'PAUSED': '暂停',
    'COMPLETED': '已完成',
    'FAILED': '失败'
};

function navigate(section) {
    // 隐藏所有内容区域
    document.querySelectorAll('#content > div').forEach(div => div.style.display = 'none');

    // 显示对应的内容区域
    document.getElementById(`${section}-content`).style.display = 'block';

    // 更新导航激活状态
    document.querySelectorAll('#nav li').forEach(li => li.classList.remove('active'));
    document.getElementById(`nav-${section}`).classList.add('active');

    // 根据导航项重新加载数据或执行相应操作
    currentPage = 1;
    itemsPerPage = 10;
    if (section === 'download') {
        fetchDownloadTaskData();
    } else if (section === 'subscribe') {
        fetchSubscribeChannelData();
    } else if (section === 'subscribe-update') {
        fetchSubscribeChannelVideoData();
    }
}

function fetchDownloadTaskData() {
    fetch(`/api/task/list?page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateDownloadTaskList)
        .catch(error => console.error('Error fetching data:', error));
}

function fetchSubscribeChannelData() {
    fetch(`/api/channel/list?page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateSubscribeChannelList)
        .catch(error => console.error('Error fetching data:', error));
}

function fetchSubscribeChannelVideoData() {
    fetch(`/api/channel/video/list?page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateSubscribeChannelVideoList)
        .catch(error => console.error('Error fetching data:', error));
}

function downloadChannelVideo(channelId, videoId) {
    fetch('/api/channel/video/download/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            channel_id: channelId,
            video_id: videoId
        })
    })
    .then(response => response.json())
    .then(data => {
        fetchSubscribeChannelVideoData();

        // 显示自定义模态框
        document.getElementById('modalMessage').innerText = '视频下载任务已成功创建！';
        document.getElementById('customModal').style.display = 'block';
        // 添加点击关闭按钮的事件监听器
        document.querySelector('.close').addEventListener('click', function() {
            document.getElementById('customModal').style.display = 'none';
        });
    })
    .catch(error =>console.error('Error:', error));
}

function markReadChannelVideo(channelId, videoId) {
    fetch('/api/channel/video/mark-read/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            channel_id: channelId,
            video_id: videoId
        })
    })
    .then(response => response.json())
    .then(data => {
        fetchSubscribeChannelVideoData();
    });
}

function updateDownloadTaskList(taskInfo) {
    var tbody = document.querySelector('#download-content table tbody');
    tbody.innerHTML = ''; // 清空现有内容以准备更新
    var tasks = taskInfo.data;
    tasks.forEach(function(task) {
        var statusText = statusMap[task.status] || '未知状态';
        var row = `<tr data-task-id="${task.id}">
            <td>${task.id}</td>
            <td  class="img-box"><img src="${task.thumbnail}" referrerpolicy="no-referrer"></td>
            <td>${task.title}</td>
            <td>${statusText}</td>
            <td>${formatBytes(task.total_size)}</td>
            <td>${task.percent}</td>
            <td>${task.speed}</td>
            <td>${task.eta}</td>
            <td>${task.created_at}</td>
            <td class="action-buttons">
                <a href="#" class="button play-button">播放</a>
                <a href="#" class="button delete-button">删除</a>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });

    generateDownloadTaskPaginationButtons(taskInfo.total);
    setupPlayVideoEventListeners();
}

function updateSubscribeChannelList(subscribeInfo) {
    var tbody = document.querySelector('#subscribe-content table tbody');
    tbody.innerHTML = ''; // 清空现有内容以准备更新
    var channels = subscribeInfo.data;
    channels.forEach(function(channel) {
        var row = `<tr>
            <td>${channel.id}</td>
            <td>${channel.channel_id}</td>
            <td>${channel.name}</td>
            <td>${channel.if_enable == 1 ? '启用' : '暂停'}</td>
            <td>${channel.if_auto_download == 1 ? '是' : '否'}</td>
            <td>${channel.url}</td>
            <td>${channel.created_at}</td>
            <td class="action-buttons">
                <a href="#" class="button" onclick="handleChannelDetailClick(${channel.id})">详情</a>
                <a href="#" class="button delete-button">删除</a>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });

    generateSubscribeChannelPaginationButtons(subscribeInfo.total);
}

function updateSubscribeChannelVideoList(subscribeChannelVideoInfo) {
    var tbody = document.querySelector('#subscribe-update-content table tbody');
    tbody.innerHTML = ''; // 清空现有内容以准备更新
    var channelVideos = subscribeChannelVideoInfo.data;
    channelVideos.forEach(function(channelVideo) {
        var row = `<tr data-channel-id="${channelVideo.channel_id}" data-video-id="${channelVideo.video_id}" >
            <td>${channelVideo.channel_name}</td>
            <td class="img-box"><img src="${channelVideo.thumbnail}" referrerpolicy="no-referrer"></td>
            <td>${channelVideo.title}</td>
            <td>${channelVideo.url}</td>
            <td>${channelVideo.uploaded_at}</td>
            <td>${channelVideo.if_downloaded == 1 ? '是' : '否'}</td>
            <td>${channelVideo.if_read == 1 ? '是' : '否'}</td>
            <td class="action-buttons">
                <a href="#" class="button download-button">下载</a>
                <a href="#" class="button delete-button" onclick="markReadChannelVideo('${channelVideo.channel_id}', '${channelVideo.video_id}')">标记</a>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });

    generateSubscribeChannelVideoPaginationButtons(subscribeChannelVideoInfo.total);
    setupChannelVideoDownloadEventListeners()
}

function handleChannelDetailClick(subscribe_id) {
    fetch(`/api/channel/detail?id=${subscribe_id}`)
        .then(response => response.json())
        .then(openChannelDetailModal)
        .catch(error => console.error('Error fetching data:', error));
}

function openChannelDetailModal(channelDetail) {
    document.getElementById('channelInfoModal').style.display = 'block';
    document.getElementById('modalSubscribeId').innerText = channelDetail.id;
    document.getElementById('modalChannelId').innerText = channelDetail.channelId;
    document.getElementById('modalChannelName').innerText = channelDetail.name;
    document.getElementById('modalChannelUrl').innerText = channelDetail.url;
    document.getElementById('modalChannelSubscribeTime').innerText = channelDetail.createdAt;
    const enableRadios = document.querySelectorAll('input[name="modalChannelIfEnable"]');
    if (channelDetail.ifEnable == 1) {
        enableRadios[0].checked = true;
    } else {
        enableRadios[1].checked = true;
    }
    const autoDownloadRadios = document.querySelectorAll('input[name="modalChannelIfAutoDownload"]');
    if (channelDetail.ifAutoDownload == 1) {
        autoDownloadRadios[0].checked = true;
    } else {
        autoDownloadRadios[1].checked = true;
    }
}

function handleChannelSaveClick(event) {
    var subscribeId = document.getElementById('modalSubscribeId').innerText.trim();
    var ifEnable = document.querySelector('input[name="modalChannelIfEnable"]:checked').value;
    var ifAutoDownload = document.querySelector('input[name="modalChannelIfAutoDownload"]:checked').value;

    // Construct the request body as JSON
    var requestBody = {
        id: subscribeId,
        ifEnable: ifEnable, // Assuming values are strings like 'true'/'false', convert to boolean if needed
        ifAutoDownload: ifAutoDownload // Same conversion if applicable
    };

    fetch(`/api/channel/update`, {
        method: 'POST', // Specify the method as POST
        headers: {
            'Content-Type': 'application/json', // Set the content type header
        },
        body: JSON.stringify(requestBody), // Convert the request body to a JSON string
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        handleChannelDetailCloseClick();
        fetchSubscribeChannelData();
    })
    .catch(error => console.error('Error updating channel:', error));
}

function handleChannelDetailCloseClick(event) {
    document.getElementById('channelInfoModal').style.display = 'none';
}

function handleDownloadClick(event) {
    event.preventDefault();
    // 在这里执行下载操作
    const row = event.target.parentNode.parentNode;
    var channelId = row.getAttribute('data-channel-id');
    var videoId = row.getAttribute('data-video-id');
    downloadChannelVideo(channelId, videoId)
}


function setupChannelVideoDownloadEventListeners() {
    var downloadButtons = document.querySelectorAll('#subscribe-update-content table tbody .download-button');
    downloadButtons.forEach(function(button) {
        button.addEventListener('click', handleDownloadClick);
    });
}


function handlePlayClick(event) {
    event.preventDefault();
    // 在这里执行下载操作
    const row = event.target.parentNode.parentNode;
    var taskId = row.getAttribute('data-task-id');
    showVideoModal(`/api/task/video/play/${taskId}`)
}


function setupPlayVideoEventListeners() {
    var playButtons = document.querySelectorAll('#download-content table tbody .play-button');
    playButtons.forEach(function(button) {
        button.addEventListener('click', handlePlayClick);
    });
}


function generateDownloadTaskPaginationButtons(total_records) {
    var pages = Math.ceil(total_records / itemsPerPage);
    var paginationDiv = document.getElementById('download-task-pagination');
    paginationDiv.innerHTML = ''; // 清空现有分页按钮

    for (var i = 1; i <= pages; i++) {
        var button = document.createElement('button');
        button.textContent = i;
        button.onclick = (function(page) {
            return function() {
                currentPage = page;
                fetchDownloadTaskData();
            };
        })(i);
        if (i === currentPage) button.classList.add('active');
        paginationDiv.appendChild(button);
   }
}

function generateSubscribeChannelPaginationButtons(total_records) {
    var pages = Math.ceil(total_records / itemsPerPage);
    var paginationDiv = document.getElementById('subscribe-channel-pagination');
    paginationDiv.innerHTML = '';

    for (var i = 1; i <= pages; i++) {
        var button = document.createElement('button');
        button.textContent = i;
        button.onclick = (function(page) {
            return function() {
                currentPage = page;
                fetchSubscribeChannelData();
            };
        })(i);
        if (i === currentPage) button.classList.add('active');
        paginationDiv.appendChild(button);
   }
}


function generateSubscribeChannelVideoPaginationButtons(total_records) {
    var pages = Math.ceil(total_records / itemsPerPage);
    var paginationDiv = document.getElementById('subscribe-channel-update-pagination');
    paginationDiv.innerHTML = ''; // 清空现有分页按钮

    for (var i = 1; i <= pages; i++) {
        var button = document.createElement('button');
        button.textContent = i;
        button.onclick = (function(page) {
            return function() {
                currentPage = page;
                fetchSubscribeChannelVideoData();
            };
        })(i);
        if (i === currentPage) button.classList.add('active');
        paginationDiv.appendChild(button);
   }
}

// 确保此函数在其他脚本执行后运行，或者将其放在所有其他脚本之后
function showVideoModal(videoUrl) {
    var videoPlayer = document.getElementById('videoPlayer');
    var videoSource = document.getElementById('videoSource');

    // 设置视频源URL
    videoSource.src = videoUrl;
    // 开启自动播放
    videoPlayer.autoplay = true;
    // 重置视频源，以便重新加载
    videoPlayer.load();

    // 显示模态框
    document.getElementById('videoPlayerModal').style.display = 'block';

    // 可选：尝试播放视频，增强兼容性
    videoPlayer.addEventListener('canplay', function() {
        videoPlayer.play().catch(function(error) {
            console.error("自动播放失败:", error);
        });
    });
}

function closeVideoModal() {
    // 获取video元素
    var videoPlayer = document.getElementById('videoPlayer');
    // 暂停视频播放
    videoPlayer.pause();
    // 隐藏视频播放模态框
    document.getElementById('videoPlayerModal').style.display = 'none';
}


function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

window.onload = function () {

    document.getElementById('nav-download').classList.add('active');

    fetchDownloadTaskData(currentPage, itemsPerPage);
    setInterval(()=> {
        fetchDownloadTaskData(currentPage, itemsPerPage);
    }, 1000)

    document.addEventListener('keydown', function(event) {
        // 检查用户是否按下了Esc键（其键码为27）
        if (event.keyCode === 27 && document.getElementById('videoPlayerModal').style.display === 'block') {
            closeVideoModal();
        }
    });
};