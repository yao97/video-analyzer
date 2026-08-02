// 在浏览器 Console 里运行这个，检查视频预览和转写功能
// 复制粘贴到 F12 Console，按回车

console.log('=== 调试开始 ===');

// 1. 检查视频预览元素是否存在
const videoEl = document.getElementById('videoPreview');
console.log('videoPreview 元素:', videoEl);
console.log('videoPreview display:', videoEl ? videoEl.style.display : 'N/A');

// 2. 检查转写服务是否可访问
fetch('http://127.0.0.1:8766/api/status/00000000')
  .then(r => r.json())
  .then(d => console.log('转写服务状态:', d))
  .catch(e => console.error('转写服务连接失败:', e));

// 3. 检查 processFile 函数是否存在
console.log('processFile 函数类型:', typeof processFile);

// 4. 手动触发视频预览测试
const testVideoPreview = () => {
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = 'video/*';
  fileInput.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    console.log('选择的文件:', file.name, file.size, 'bytes');
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.src = URL.createObjectURL(file);
    video.onloadedmetadata = () => {
      console.log('视频元数据加载成功:', video.videoWidth, 'x', video.videoHeight);
      if (videoEl) {
        videoEl.src = video.src;
        videoEl.style.display = 'block';
        videoEl.load();
        console.log('视频预览已设置');
      }
    };
    video.onerror = (err) => console.error('视频加载失败:', err);
  };
  fileInput.click();
};

console.log('如需测试视频预览，运行: testVideoPreview()');
window.testVideoPreview = testVideoPreview;

console.log('=== 调试结束 ===');
