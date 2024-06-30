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
    fetch(`http://localhost:8000/api/task/list?page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateDownloadTaskList)
        .catch(error => console.error('Error fetching data:', error));
}

function fetchSubscribeChannelData() {
    fetch(`http://localhost:8000/api/channel/list?page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateSubscribeChannelList)
        .catch(error => console.error('Error fetching data:', error));
}

function fetchSubscribeChannelVideoData() {
    fetch(`http://localhost:8000/api/channel/video/list?page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateSubscribeChannelVideoList)
        .catch(error => console.error('Error fetching data:', error));
}

function updateDownloadTaskList(taskInfo) {
    var tbody = document.querySelector('#download-content table tbody');
    tbody.innerHTML = ''; // 清空现有内容以准备更新
    var tasks = taskInfo.data;
    tasks.forEach(function(task) {
        var statusText = statusMap[task.status] || '未知状态';
        var row = `<tr>
            <td>${task.id}</td>
            <td>${task.title}</td>
            <td>${statusText}</td>
            <td>${formatBytes(task.total_size)}</td>
            <td>${task.percent}</td>
            <td>${task.speed}</td>
            <td>${task.eta}</td>
            <td>${task.created_at}</td>
            <td class="action-buttons">
                <a href="#" class="button">详情</a>
                <a href="#" class="button delete-button">删除</a>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });

    generateDownloadTaskPaginationButtons(taskInfo.total);
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
            <td>${channel.url}</td>
            <td>${channel.created_at}</td>
            <td class="action-buttons">
                <a href="#" class="button">详情</a>
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
        var row = `<tr>
            <td>${channelVideo.channel_name}</td>
            <td>${channelVideo.title}</td>
            <td>${channelVideo.url}</td>
            <td>${channelVideo.uploaded_at}</td>
            <td>${channelVideo.if_downloaded == 1 ? '是' : '否'}</td>
            <td>${channelVideo.created_at}</td>
            <td class="action-buttons">
                <a href="#" class="button">下载</a>
                <a href="#" class="button delete-button">删除</a>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });

    generateSubscribeChannelVideoPaginationButtons(subscribeChannelVideoInfo.total);
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
        console.log(data);
        fetchDownloadTaskData(currentPage, itemsPerPage);
    })
    .catch(error =>console.error('Error:', error));
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

    document.sele
};