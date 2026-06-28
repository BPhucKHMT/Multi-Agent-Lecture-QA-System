---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- generated_from_trainer
- dataset_size:25194
- loss:CachedMultipleNegativesRankingLoss
base_model: BAAI/bge-m3
widget:
- source_sentence: Gradient trong quá trình cập nhật tham số thực sự cho chúng ta
    biết điều gì về hướng đi của các tham số trong model?
  sentences:
  - . ở trên là xác suất dự đoán cho mẫu thứ Thì bước đầu tiên là chúng ta khởi tạo
    các tham số của mô hình cụ thể là W và B với giá trị ban đầu có thể là zero hoặc
    là một con số ngẫu nhiên nhỏ. Tiếp theo thì nó là một quá trình lặp của quá trình
    cập nhật các tham số này dựa trên cái gradient cho tới khi hội tụ. Thì ở mỗi vòng
    lặp thì chúng ta sẽ tính toán đạo hàm của hàm chi phí đối với từng tham số W và
    B như trên màn hình. Thì giá trị gradient này cho biết hướng thay đổi của hàm
    chi phí nếu chúng ta điều chỉnh các tham số. Thế thì để giảm hàm chi phí thì ta
    cập nhật W và B theo hướng ngược lại
  - với y thì đây là hằng số do đó chúng ta sẽ là đạo hàm bằng 0 trừ cho 2y và trừ
    6 và đạo hàm của x theo y sẽ là bằng 5y trừ cho 2y và trừ 6 thì đây chính là vector
    gradient theo biến x và y đây là x và y rồi thì đây là kết quả của mình và các
    mô hình học sâu của chúng ta thì đều dựa trên lý thuyết hoặc dựa trên ký hiệu
    của gradient mục tiêu của gradient là xác định xem từng thành phần vector của
    mình từng thành phần x1, x2 cho đến xn nó ảnh hưởng như thế nào lên trên sự tăng
    giảm của hàm số và khi chúng ta xác định được sự ảnh hưởng đó rồi thì chúng ta
    sẽ cập nhật lại x1, x2, xn sau cho f của mình tiến về giá trị cực tiểu hoặc giá
    trị cực đại và tăng giảm của gradient trong mô hình này
  - Tiếp theo chúng ta sẽ cùng ôn tập toán giải tích nếu như đại số tuyến tính là
    công cụ để giúp chúng ta có thể biến đổi dữ liệu thì giải tích là cung cấp cho
    chúng ta một cái công cụ để biểu diễn các cái chuỗi, các phép biến đổi và đồng
    thời đó là một cái công cụ để giúp chúng ta giải quyết các cái bài toán tối ưu
    và đặc biệt trong cái môn này của chúng ta, đó là máy học nâng cao chúng ta sẽ
    dựa trên các cái mô hình dựa Gradient tức là dùng vector đạo hàm để mà chúng ta
    đi cập nhật tham số và huấn luyện mô hình khi đó là chúng ta sẽ có một cái công
    cụ nữa đó chính là đạo hàm và đạo hàm thì ban đầu sẽ giúp chúng ta khảo sát cái
    hàm số rồi sau đó sẽ giúp chúng ta tìm được các cái điểm cực tiểu
  - . Và cuối cùng bài toán tối ưu này thường được giải bằng thuật toán Gradient Descent
    giúp mô hình từng bước điều chỉnh các tham số để tiến gần đến điểm cực tiểu toàn
    cục của hàm chi phí.
  - rất là nhỏ Ví dụ như con số mà bé hơn một Thì khi chúng ta nhân các cái con số
    bé hơn một thì nó sẽ có xu hướng tiến về không Trong cái quá trình cập nhật cái
    tham số của mình mà mục tiêu của cái việc cập nhật cái tham số này là để cho đạo
    hàm của mình càng lúc càng nhỏ, và gradient descent gradient descent tức là đạo
    hàm càng lúc càng giảm thì khi đạo hàm càng giảm thì các thành phần này càng lúc
    càng giảm các thành phần này càng lúc càng giảm thì dẫn đến đó là các con số nhỏ
    mà nhân với nhau sẽ tiến về 0 và khi đạo hàm xấp xỉ bằng 0 tức là bước nhảy theta
    này gần như không cập nhật nó gần như không cập nhật thì đó chính là hiện tượng
    vanishing gradient nó sẽ làm cho quá trình huấn luyện
  - . Từ thời điểm xuất phát này thì chúng ta sẽ cập nhật các tham số từng bước một
    dựa vào gradient tức là độ dốc của hàm tại vị trí hiện tại. Gradient thì cho chúng
    ta biết hướng và độ lớn của sự thay đổi. Để giảm hàm chi phí ta sẽ điều chỉnh
    tham số ngược lại theo hướng của gradient. Độ lớn của mỗi bước điều chỉnh này
    được kiểm soát bởi một siêu tham số. gọi là learning rate (tốc độ học) ký hiệu
    là alpha. Learning rate là quyết định mỗi lần cập nhật chúng ta sẽ bước một đoạn
    lớn hay nhỏ trên con đường đi xuống thung lũng
- source_sentence: Làm thế nào để tính đạo hàm của hàm fxi?
  sentences:
  - . đạo hàm của f theo theta đạo hàm của f theo theta n thì trong các cái mô hình
    máy học thì chúng ta xây dựng là cái tham số theta nhưng mà để sử dụng cái mô
    hình máy học thì chúng ta sẽ dùng biến f và biến x ở đây thì ở đây chúng ta sẽ
    có một cái ví dụ là fxi là bằng cái gì? hàm như đã cho trên thì gradient của f
    theo x thì nó sẽ là bằng một cái vector của hàm f đạo hàm của f theo biến x và
    đạo hàm của f theo biến y và đạo hàm của f theo biến y thì đạo hàm của x theo
    y sẽ là bằng 5y trừ cho 14x còn đây là hằng số đối với x nên nó sẽ bỏ đi, cộng
    3 còn đạo hàm của f theo y thì sẽ là bằng 5x đối với y thì đây là hằng số do đó
    chúng ta sẽ là đạo hàm bằng 0 trừ cho 2y và trừ 6 và đạo hàm của x
  - chúng ta triển khai ở đây thì f1 i chính là chúng ta xem nó như là một cái biến
    Rồi chúng ta triển khai vô thì nó sẽ là z nhân với lại cái biến Tức là z nhân
    với f1, mà f1 thì nó lại là bằng x cộng i Rồi, khi đó chúng ta sẽ tính đạo hàm
    Đạo hàm là d của f1 theo i D của f1 theo i thì nó sẽ là bằng 1 Tại trong có mắt
    của i thì x là bằng hằng số D của f2 theo f1 Tức là đạo hàm của công thức này
    Và đạo hàm của công thức này là bằng z Rồi, như vậy thì chúng ta sẽ có đạo hàm
    của f theo biến i Chính là bằng đạo hàm của f2 theo f1 Nhân cho đạo hàm của f1
    theo i Vì f2 theo f1 chính là bằng z Và df1 theo i chính là bằng 1, không bằng
    z Tương tự như vậy chúng ta sẽ tính cho đạo hàm của f theo z Thì
  - . Thì đây là một cái ví dụ. Ở đây chúng ta sẽ có f của mình sẽ là, fx sẽ là bằng
    x bình phương, cộng 1. Và gx sẽ là sin x. Thì khi đó cái hàm hợp của 2 cái hàm
    trên sẽ ký hiệu là y bằng g của fx sẽ bằng. Chúng ta sẽ thực hiện cái thao tác
    f trước. F trước, tức là chúng ta sẽ tính cái x bình cộng 1 trước, sau đó sẽ đưa
    vào cho hàm sin thực hiện sau. Thì ở đây chúng ta sẽ có một số bài tập các bạn
    có thể tự làm một cách dễ dàng. Tiếp theo thì chúng ta sẽ tìm hiểu về đạo hàm,
    như đã đề cập trước đây. Đây là một trong những công cụ quan trọng để giúp chúng
    ta tìm được mô hình tối ưu
  - . Và như đã đề cập ở trước thì mô hình của mình sẽ là một chuỗi các hàm số Chuỗi
    các biến đổi hay là chuỗi các hàm số Do đó thì một công cụ khác cũng rất quan
    trọng Đó chính là đạo hàm của hàm hợp Tiếp theo thì chúng ta sẽ tìm hiểu về các
    dạng hàm toán học Nếu như biểu diễn một cách đơn giản thì chúng ta có thể ghi
    là y là một hàm số bằng fx Với x là cái biến số đầu vào và y chính là cái giá
    trị của cái hàm số này Một cách biểu diễn khác, đó là chúng ta biểu diễn dưới
    dạng là sơ đồ Chúng ta sẽ có một input x và qua cái hàm f thì chúng ta sẽ tính
    ra được cái giá trị output là fx Đây là kết quả của một phép biến đổi của hàm
    F với thông tin đầu vào là x Thì đây chúng ta chỉ ôn lại khái niệm
  - z nhân cho xx, trong trường hợp này chính là f1 F1 chúng ta sẽ thế vào bằng công
    thức này, đó là x cộng i Rồi, khi đó thì đạo hàm của f1 theo x, lưu ý là ở đây
    chúng ta chỉ đang xét với một biến x thôi Chúng ta sẽ làm cái việc tương tự, cái
    việc này tương tự cho biến i, chúng ta sẽ làm sao Đạo hàm của f1 theo x, thì đạo
    hàm của f1 theo x chính là trong công mắc của x, thì i chính là hằng số Do đó
    đạo hàm của f1 theo x chính là 1 Rồi, đạo hàm của f2 theo f1 là bao nhiêu? Đạo
    hàm của f2 theo f1, tức là chúng ta sẽ tính đạo hàm của cái này theo x Chúng ta
    sẽ tính đạo hàm của cái này theo x, thì trong biến x, thì z chính là hằng số do
    đó đạo hàm của cái này sẽ là bằng z Đạo hàm của f2 theo f1
  - mô hình diffusion thì chúng ta phải nhắc lại cái khái niệm tích phân một chút
    xíu nhưng mà ở góc độ là lập trình thì chúng ta sẽ không cần dùng đến tích phân
    mà chúng ta dùng nhiều đến cái hàm tính tổng trên những cái dải giá trị cái miền
    giá trị thì ở đây chúng ta sẽ có một cái ví dụ hàm fxi là một cái hàm như thế
    này và chúng ta sẽ đi tính đạo hàm của fxi này theo x thì nó sẽ là bằng 4x và
    đạo hàm của f theo y thì nó sẽ là bằng trừ 3 cuối cùng đó là chúng ta sẽ cùng
    tìm hiểu đến cái khái niệm gradient toàn bộ môn này thì đều dựa trên gradient
    để chúng ta xây dựng mô hình nó gọi là mô hình dựa trên gradient tức là các cái
    mô hình này đều sử dụng gradient như là một cái công cụ để cho chúng
- source_sentence: Có cách nào để truy xuất và cập nhật giá trị trong một NumPy array
    không, và cần lưu ý điều gì?
  sentences:
  - sẽ cùng predict ví dụ như chúng ta tính giá trị là tại 7 khi chúng ta dóng lên,
    thì chiếu bên đây đâu đó phải ra là 27 hay 28 gì đấy thì nó mới đúng, bây giờ
    chúng ta sẽ truyền vô giá trị là 7 Rồi, nó báo sai ở cái dòng này ở đây nó sẽ
    không thể truyền vào giá trị Scalar mà chúng ta phải truyền vào giá trị dạng Numpy
    Array np.array x.reshape(-1, 1) x là 7 rồi chúng ta sẽ để chạy thử Vậy thì nó
    sẽ là 28 đúng như hồi nãy chúng ta dự đoán nếu giá trị 7 chiếu lên trên đường
    thẳng này sau đó chiếu qua đây thì nó sẽ phải ra giá trị 27-28 với mô hình của
    mình là 28.6 Vì vậy, qua cái demo này, chúng ta đã tiến hành cài đặt mô hình Linear
    Regression với 3 phiên bản
  - . Ví dụ như là `int64`. Đó thì ở đây chúng ta chạy thử ha. Kiểu dữ liệu của mình
    là kiểu `int64` nè, `float64` nè, và số thực à số nguyên `int64`. Rồi array mà,
    tức là array có hỗ trợ các cái thao tác tính toán, có hỗ trợ các thao tác số học.
    Thì ở đây chúng ta có một cái lưu ý quan trọng. Nếu như cái NumPy array của mình
    nó có các cái hàm nào mà đã được cài đặt sẵn rồi thì chúng ta ưu tiên sử dụng
    những hàm đó thay vì chúng ta cài đặt lại. Ở đây chúng ta thấy là cái hàm tính
    tổng tất cả các phần tử trong array A có 100 triệu phần tử, có 100 triệu phần
    tử thì nếu như chúng ta thực hiện cái lệnh này nó chỉ tốn của chúng ta có 76 ms
  - dữ liệu của a là gì rồi kích thước theo từng chiều hoặc là dimension của a là
    gì thì chúng ta sẽ có lệnh là a.shape rồi chúng ta muốn truy xuất đến ba cái phần
    tử đầu tiên thì cái cách thức chúng ta truy xuất cũng giống như trong list là
    a mở ngoặc vuông 0 a mở ngoặc vuông 1 và a[2] và cái cách thức chúng ta thay đổi
    cái giá trị của mình cũng tương tự như list đó là A0 là bằng 5 rồi và a sau khi
    chúng ta cập nhật xong thì chúng ta sẽ có giá trị như thế nào thì chúng ta sẽ
    in ra màn hình thì ở đây ta sẽ in ra ha A của mình type của nó đó là kiểu NumPy
    array ndarray thì nd là dimension tức là số chiều và array là kiểu array và trong
    cái ví dụ này thì chúng ta thấy đây là một vector nên số
  - . Rồi chúng ta sẽ trực quan, chúng ta sẽ xem cái dữ liệu đó hiển thị lên trên
    màn hình như thế nào. Và một phần cũng rất là quan trọng trong cái thư viện NumPy
    này và được sử dụng cũng rất là thường xuyên đó chính là array shape và reshape.
    Array shape là cái cơ chế là cái phương thức để giúp cho chúng ta biết cái array
    của mình nó có kích thước là bao nhiêu, nó có bao nhiêu chiều và kích thước cho
    từng chiều là bao nhiêu. Ví dụ đây là một cái array có cái số chiều là 1 nhưng
    mà cái kích thước cho từng chiều của mình nó là 3. Như vậy nó sẽ là 3. Đối với
    cái array này thì cái shape của của nó nó sẽ là bao nhiêu đó. Shape ở đây nó sẽ
    là 2 3. Tức là đây là một cái array có hai chiều
  - . Cái gì đó thì như vậy thì nó sẽ tiết kiệm được cho chúng ta trong cái gọi là
    câu lệnh của mình nó gọn gàng hơn à các cái bước đầu tiên khi chúng ta tìm hiểu
    đó chính là khởi tạo một cái array như thế nào thì nếu như trong kiểu dữ liệu
    list các cái phần tử của mình Nó sẽ phải có cùng à khác kiểu dữ liệu cũng được
    đúng không Nhưng mà trong NumPy array thì các cái phần tử của mình nó phải là
    những phần tử cùng kiểu dữ liệu thì ví dụ chúng ta thấy đây là chúng ta đang khởi
    tạo ra một cái array một chiều với các cái con số nguyên có giá trị lần lượt là
    1 2 3 đó thì khi chúng ta tạo ra thì chúng ta sẽ có một cái NumPy array có giá
    trị như thế này rồi và điều gì xảy ra nếu như chúng ta đang xen
  - . Rồi kiểu dữ liệu thì trong NumPy nó có hỗ trợ các cái kiểu dữ liệu nào khi chúng
    ta xây dựng một cái array đúng không? Thì ở trong cái array thì nó sẽ phải thỏa
    mãn một tính chất đó là tất cả các cái giá trị trong cùng một cái array nó phải
    cùng một cái kiểu dữ liệu. Thế thì cái kiểu dữ liệu mà NumPy array nó hỗ trợ đó
    là những cái dữ liệu gì? Ví dụ như NumPy array sẽ hỗ trợ dữ liệu là kiểu số nguyên
    hoặc là số thực hoặc là boolean. Và ngoài những kiểu này ra thì còn những kiểu
    nào hay không? Rồi NumPy còn hỗ trợ các cái thao tác là copy và view dữ liệu.
    Copy tức là chúng ta sẽ tạo một cái đối tượng mới từ một cái array cũ hay là chúng
    ta clone cái dữ liệu của mình ra như thế nào
- source_sentence: X lim và Y lim có vai trò gì trong việc tách lớp dữ liệu?
  sentences:
  - ở đây và nó chạm vào những điểm màu xanh thì khoảng cách từ biên trái sang biên
    phải sẽ gọi là margin và các điểm nằm trên các biên trái và biên phải này là support
    vector thì đây là hình ảnh để minh họa cho cả 3 khái niệm mà chúng ta đã nói ở
    trên thế thì đối với dữ liệu, chúng ta sẽ xem xét một tình huống đơn giản trước
    đó là dữ liệu của mình, nó có một mối quan hệ tuyến tính hay là Linear Data thì
    đây là dữ liệu có thể phân tách được bởi 1 siêu phẳng thì chúng ta nhìn cái hình
    này chúng ta thấy một cách trực quan thì chúng ta thấy là có thể phân chia được
    ra làm 2 phần bằng 1 đường thẳng thì phân lớp SVM trong dữ liệu **tuyến tính**
    cho tập dữ liệu gồm 2 lớp ví dụ như ở đây chúng ta có 2
  - . Còn hồi quy thì đầu ra của cái hàm của mình nó sẽ là một cái giá trị dự đoán
    liên tục. Và cái việc ước lượng các hàm phân loại hoặc hồi quy này thì nó sẽ được
    dựa trên các cái cặp dữ liệu. các cái cặp dữ liệu có cái nhãn thì nhãn ở đây trong
    trường hợp này đó chính là giá trị Y. Thì Y ở đây nó được gọi là nhãn hay còn
    gọi là label. Và ở trên hình ví dụ ở đây chúng ta thấy là các cái tập à các cái
    điểm của mình sẽ được gán bởi hai cái nhãn đó là hình tròn và chữ X thì tương
    ứng là hai cái phân lớp. Và tập dữ liệu huấn luyện của mình thì bao gồm là x1,
    y1. Trong đó cái chỉ số ở phía trên là cho biết cái thứ tự của cái mẫu dữ liệu
    của mình. Đây là mẫu dữ liệu thứ à đây là mẫu thứ thứ nhất
  - . À nhưng mà vì nó nhanh quá nên nó bị phân kỳ. Nó cứ chạy qua chạy lại nó bị
    phân kỳ. Rồi ở đây chúng ta sẽ để lại là 0.01 và x ở đây thì có thể chúng ta chỉ
    lấy trong cái phạm vi là -30 cho đến khoảng 5 thôi. À ở đây chúng ta bị nhầm ha.
    Tức là ở đây là xlim còn đây phải là ylim mới đúng. Tức là trục tung của mình
    là phải từ -50 cho đến khoảng là 5 thôi. Đó thì chúng ta thấy là cái mô hình của
    chúng ta đang tìm cách để fit vào. Chúng ta thấy là càng lúc nó đang fit vào các
    cái điểm nè. Nó bẻ cái đường bậc B để cho nó đi qua các cái điểm của mình. Tương
    tự như vậy, ở đây nó cũng sẽ cố gắng bẻ cái đường bậc B để đi qua các cái điểm
    của mình
  - Sau đây thì chúng ta sẽ đến với một trong những cái thuật toán nổi tiếng đó là
    à để mà phân cụm đó chính là thuật toán Camin. Và Camin là một trong những cái
    thuật toán mà được bình chọn là top 10 thuật toán trong lĩnh vực về à khai thác
    dữ liệu, data mining và được sử dụng rất là phổ biến. Thì camin là một thực toán
    phân cụm theo kiểu là phân hoạch. Và chúng ta ký hiệu gọi cái tập dữ liệu điểm
    của mình là D. Và D này là bao gồm M m mẫu dữ liệu X1, X2 cho đến XM. Thì trong
    đó xy là một cái vecơ trong không gian cái giá trị thực và xy này thì thuộc R.
    Trong đó R là à R này chính là số thuộc tính hoặc là số chiều của cái dữ liệu
    của mình. Tức là XY này nè là một cái vecơ có R chiều
  - . Và tương tự như vậy cho Yim thì chúng ta sẽ kéo là từ 0 cho đến 4. Rồi ở trên
    đây cũng vậy. Đó thì chúng ta sẽ thấy là khi chúng ta cố định cái X lim và Y lim
    á limit á thì nó sẽ không có bị bép bóp méo cái cái khung hình của mình. Và ban
    đầu thì nó sẽ nằm ở tuốc phía bên dưới. Cái mô hình của mình nó sẽ nằm cái đường
    boundary của mình nó nằm tuốc ở bên dưới. Sau đó chúng ta thấy là nó đã tịnh tiến
    dần đúng không? Nó tịnh tiến dần về khu vực này. Sau rồi nó sẽ xoay xoay lại để
    tách nó ra làm hai. Thì ở đây chúng ta có thể cho nó chậm hơn một chút để chúng
    ta hình dung cái cách mà nó chạy ha. Chúng ta nâng lên đó là khoảng 0.3 đi. Chậm
    lại khoảng ba lần
  - . Đó là một tiêu chí để chúng ta phân chia thành các vùng tốt hơn Tuy nhiên, đối
    với lại bài toán phân loại thì chúng ta sẽ có 2 chỉ số khác đó là chỉ số Gini
    và chỉ số entropy 2 chỉ số này có thể đánh giá được một cây có phân loại tốt hay
    là không Cụ thể hơn, chỉ số Gini được định nghĩa bằng công thức sau Giả sử chúng
    ta sẽ có một vùng dữ liệu cố định Thì ở đây chúng ta có thể hình dung là vùng
    dữ liệu đó bao gồm 3 điểm dữ liệu ứng với lại bài toán phân loại X và O Các hạng
    mục này là 2 chẳng hạn, chúng ta sẽ có 2 lớp Khi thế vào công thức Gini, chúng
    ta sẽ có lớp thứ nhất là lớp O Xác suất xuất hiện của nó là 1 chẳng hạn, thành
    phần thứ nhất là 0 Lớp thứ 2 là lớp X, chúng ta sẽ thay thế
- source_sentence: Chỉ số index có ảnh hưởng gì đến nhãn dự đoán không, và tại sao
    chúng ta cần quan tâm đến điều này?
  sentences:
  - . tyel as plp rồi plt ch chúng ta sẽ sử dụng cái hàm đó là Imo hàm Ino với cái
    biến là x và x này á thì nó có các cái phần thc cái chiều đó là 60.000 nh 28 x
    28 thì ở chiều đầu tiên chúng ta sẽ lấy ra tại một cái vị trí nào đó đó là Index
    và trong trường hợp này thì chúng ta sẽ cho Index là bằng 123 cái con số bất kỳ
    trong khoảng từ 1 từ 0 cho đến 60.000 rồi à thành phần còn lại thì sẽ là hai chấm
    hai chấm tức là chúng ta sẽ lấy toàn bộ Cái nội dung của Tấm ảnh ra để chúng ta
    hiển thị rồi sau đó chúng ta sẽ thực hiện thì thấy là cái ảnh này mình đoán đoán
    đó hình như là số 7 thì muốn biết chính xác nó là nhãn bao nhiêu thì chúng ta
    sẽ in ra là à nhãn của dữ liệu đó rồi Ở đây chúng ta sẽ lấy
  - . Còn hồi quy thì đầu ra của cái hàm của mình nó sẽ là một cái giá trị dự đoán
    liên tục. Và cái việc ước lượng các hàm phân loại hoặc hồi quy này thì nó sẽ được
    dựa trên các cái cặp dữ liệu. các cái cặp dữ liệu có cái nhãn thì nhãn ở đây trong
    trường hợp này đó chính là giá trị Y. Thì Y ở đây nó được gọi là nhãn hay còn
    gọi là label. Và ở trên hình ví dụ ở đây chúng ta thấy là các cái tập à các cái
    điểm của mình sẽ được gán bởi hai cái nhãn đó là hình tròn và chữ X thì tương
    ứng là hai cái phân lớp. Và tập dữ liệu huấn luyện của mình thì bao gồm là x1,
    y1. Trong đó cái chỉ số ở phía trên là cho biết cái thứ tự của cái mẫu dữ liệu
    của mình. Đây là mẫu dữ liệu thứ à đây là mẫu thứ thứ nhất
  - . tức là chúng ta sẽ lấy toàn bộ nội dung của tấm ảnh ra để chúng ta hiển thị
    rồi sau đó chúng ta sẽ thực hiện thì thấy là cái ảnh này mình đoán đoán nó hình
    như là số 7 thì muốn biết chính xác đó là nhãn bao nhiêu thì chúng ta sẽ in ra
    là nhãn của dữ liệu Rồi, ở đây chúng ta sẽ lấy là y_train và chúng ta cũng sẽ
    truyền vào cái chỉ số là index Rồi, đúng như dự đoán thì cái nhãn này chính là,
    nhãn của dữ liệu này chính là số 7 và chúng ta có thể thay đổi các cái chỉ số
    này, ví dụ như là 10.000 Rồi, thì đây là tương ứng nhãn của nó sẽ là số 3. Tiếp
    theo, đó là chúng ta sẽ tiền xử lý, chúng ta sẽ chuẩn hóa dữ liệu X_train và X_test
    của mình
  - là khoảng cách đến trung tâm thành phố Thì đây chính là các cái biến số để giúp
    cho chúng ta đưa ra được cái dự đoán Cái nhãn của một mẫu dữ liệu sẽ là cái giá
    trị Y
  - . Rồi sau đó chúng ta sẽ thực hiện thì thấy là cái ảnh này mình đoán đoán nó hình
    như là số 7. Thì muốn biết chính xác đó là nhãn bao nhiêu thì chúng ta sẽ in ra
    là nhãn của dữ liệu. Rồi ở đây chúng ta sẽ lấy là y_train và chúng ta cũng sẽ
    truyền vào cái trị số là index. Rồi đúng như dự đoán thì cái nhãn này chính là,
    nhãn của dữ liệu này chính là số 7. Và chúng ta có thể thay đổi các cái trị số
    này, ví dụ như là 10.000. Rồi, thì đây là tương ứng nhãn của nó sẽ là số 3. Tiếp
    theo, đó là chúng ta sẽ tiền xử lý chúng ta sẽ chuẩn hóa cái dữ liệu X_train và
    X_test của mình. Bằng cách đó là thay vì đưa cái miền giá trị từ 0 đến 255, thì
    chúng ta sẽ đưa về cái miền giá trị là từ 0 cho đến 1
  - . Ở đây chúng ta sẽ để là predict, nhãn dự đoán là y_pred. Rồi còn ở đây sẽ là
    nhãn thực tế. Và ở đây cái chỉ số này chúng ta sẽ tham số hóa nó là idx là bằng
    100 ví dụ vậy. Và chúng ta sẽ để đây là idx. Rồi đó thì đại đa số chúng ta thấy
    là cái độ chính xác rất là cao. Chúng ta thử rất nhiều những cái nhãn khác nhau
    ha. Đó thì nó đều ra là dự đoán và thực tế khớp với nhau. Bây giờ trong cái mô
    hình thì chúng ta thấy nó có rất nhiều những cái module khác nhau. Và tại thời
    điểm hiện tại thì chúng ta sẽ chưa hiểu rõ cái vai trò của từng module này
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on BAAI/bge-m3

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3). It maps sentences & paragraphs to a 1024-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, text classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) <!-- at revision 5617a9f61b028005a4858fdac845db406aefb181 -->
- **Maximum Sequence Length:** 384 tokens
- **Output Dimensionality:** 1024 dimensions
- **Similarity Function:** Cosine Similarity
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'max_seq_length': 384, 'do_lower_case': False, 'architecture': 'XLMRobertaModel'})
  (1): Pooling({'word_embedding_dimension': 1024, 'pooling_mode_cls_token': True, 'pooling_mode_mean_tokens': False, 'pooling_mode_max_tokens': False, 'pooling_mode_mean_sqrt_len_tokens': False, 'pooling_mode_weightedmean_tokens': False, 'pooling_mode_lasttoken': False, 'include_prompt': True})
  (2): Normalize()
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'Chỉ số index có ảnh hưởng gì đến nhãn dự đoán không, và tại sao chúng ta cần quan tâm đến điều này?',
    '. tức là chúng ta sẽ lấy toàn bộ nội dung của tấm ảnh ra để chúng ta hiển thị rồi sau đó chúng ta sẽ thực hiện thì thấy là cái ảnh này mình đoán đoán nó hình như là số 7 thì muốn biết chính xác đó là nhãn bao nhiêu thì chúng ta sẽ in ra là nhãn của dữ liệu Rồi, ở đây chúng ta sẽ lấy là y_train và chúng ta cũng sẽ truyền vào cái chỉ số là index Rồi, đúng như dự đoán thì cái nhãn này chính là, nhãn của dữ liệu này chính là số 7 và chúng ta có thể thay đổi các cái chỉ số này, ví dụ như là 10.000 Rồi, thì đây là tương ứng nhãn của nó sẽ là số 3. Tiếp theo, đó là chúng ta sẽ tiền xử lý, chúng ta sẽ chuẩn hóa dữ liệu X_train và X_test của mình',
    '. tyel as plp rồi plt ch chúng ta sẽ sử dụng cái hàm đó là Imo hàm Ino với cái biến là x và x này á thì nó có các cái phần thc cái chiều đó là 60.000 nh 28 x 28 thì ở chiều đầu tiên chúng ta sẽ lấy ra tại một cái vị trí nào đó đó là Index và trong trường hợp này thì chúng ta sẽ cho Index là bằng 123 cái con số bất kỳ trong khoảng từ 1 từ 0 cho đến 60.000 rồi à thành phần còn lại thì sẽ là hai chấm hai chấm tức là chúng ta sẽ lấy toàn bộ Cái nội dung của Tấm ảnh ra để chúng ta hiển thị rồi sau đó chúng ta sẽ thực hiện thì thấy là cái ảnh này mình đoán đoán đó hình như là số 7 thì muốn biết chính xác nó là nhãn bao nhiêu thì chúng ta sẽ in ra là à nhãn của dữ liệu đó rồi Ở đây chúng ta sẽ lấy',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 1024]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.4708, 0.3935],
#         [0.4708, 1.0000, 0.4565],
#         [0.3935, 0.4565, 1.0000]])
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 25,194 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, <code>sentence_2</code>, <code>sentence_3</code>, <code>sentence_4</code>, <code>sentence_5</code>, and <code>sentence_6</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                         | sentence_1                                                                           | sentence_2                                                                           | sentence_3                                                                           | sentence_4                                                                           | sentence_5                                                                           | sentence_6                                                                           |
  |:--------|:-----------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|
  | type    | string                                                                             | string                                                                               | string                                                                               | string                                                                               | string                                                                               | string                                                                               | string                                                                               |
  | details | <ul><li>min: 11 tokens</li><li>mean: 21.69 tokens</li><li>max: 40 tokens</li></ul> | <ul><li>min: 27 tokens</li><li>mean: 161.79 tokens</li><li>max: 232 tokens</li></ul> | <ul><li>min: 13 tokens</li><li>mean: 159.82 tokens</li><li>max: 227 tokens</li></ul> | <ul><li>min: 15 tokens</li><li>mean: 162.71 tokens</li><li>max: 226 tokens</li></ul> | <ul><li>min: 13 tokens</li><li>mean: 162.44 tokens</li><li>max: 226 tokens</li></ul> | <ul><li>min: 13 tokens</li><li>mean: 164.14 tokens</li><li>max: 222 tokens</li></ul> | <ul><li>min: 13 tokens</li><li>mean: 164.06 tokens</li><li>max: 224 tokens</li></ul> |
* Samples:
  | sentence_0                                                                                                             | sentence_1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | sentence_2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | sentence_3                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | sentence_4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | sentence_5                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | sentence_6                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
  |:-----------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
  | <code>Có những phương pháp nào để tách biệt hai lớp màu bằng đường cong trong không gian dữ liệu không?</code>         | <code>. Thế thì để ạ neuro nhân tạo thì chúng ta sẽ phải có một cái tập dữ liệu để thực nghiệm. Thì cụ thể ở đây đó là tập bao gồm hai cái vòng tròn. lồng nhau. Thì với cái tập dữ liệu là hai màu đỏ và màu xanh chúng ta thấy ở đây thì đây là một cái tập dữ liệu mà nó có tính chất phi tuyến tính. Thế thì cái tính chất phi tuyến tính á nó thể hiện ở chỗ nào? Cái tính chất phi tuyến tính nó thể hiện ở chỗ là không thể chia hai cái tập ờ màu đỏ và màu xanh này bằng duy nhất một cái đường thẳng. Chúng ta thấy là với cái đường thẳng này thì nó chỉ có thể tách ra là màu đỏ và một vùng còn lại là vừa có đỏ và xanh. Đó. Hoặc đường này thì chúng ta thấy là nó chia ra làm hai phần</code>                       | <code>nó làm 2 đây là một cái siêu phẳng mới trong một cái không gian mới thay vì chúng ta tìm nó trong không gian osz thì chúng ta tìm nó trong cái không gian osz Như vậy thì trong tình huống dữ liệu không có tuyến tính hay là phi tuyến tính thì dữ liệu của mình không thể phân tác được hoàn toàn bằng một đường thẳng hay là siêu phẳng duy nhất trong không gian góc thì ở đây chúng ta sẽ có một số tình huống ở bên trái là Linear Separable tức là có thể tìm được một siêu phẳng chia tách làm 2 còn 2 tình huống bên đây là Non-linear Separable thì các cái điểm này nó sẽ được phân tác ra bởi những cái đường cong như thế này hoặc là trong tình huống này thì là một cái đường cong kép kín như thế này thì</code>   | <code>mô hình truyền thống trước đây chỉ hiệu quả được với những dữ liệu có thể phân tách một cách tuyến tính Tức là chúng ta chỉ có thể vẽ được một đường thẳng để chia nó ra làm hai phần Thì đây là một đường tuyến tính để tách ra hai điểm màu vàng, màu cam và màu xanh Tuy nhiên trong thực tế thì dữ liệu của mình thường có một mối quan hệ rất phức tạp và thường sẽ là phi tuyến tính Ví dụ như các loại dữ liệu hình ảnh và dữ liệu văn bản để mà chúng ta có thể nhận diện được hình ảnh hoặc là phân loại văn bản vân vân thì đó là những bài toán mà không phải là có một mối quan hệ tuyến tính thì ở trong hình bên tay trái ở đây chúng ta sẽ thấy là 2 tập là màu xanh và màu cam thì nó sẽ không thể nào có</code> | <code>. Đó. Hoặc đường này thì chúng ta thấy là nó chia ra làm hai phần. Tuy nhiên cả hai phần thì đều có các điểm màu đỏ và màu xanh. Như vậy thì rõ ràng không thể nào có thể chia tách ra được bằng một đường thẳng. Mà nếu muốn chia tách được thì chúng ta sẽ phải có một cái đường cong như thế này thì mới có thể chia ra làm hai phần thôi. Như vậy thì trong cái tập dữ liệu mà có tính chất phi tuyến tính này và lưu ý là cái dữ liệu này nó cũng chỉ mới là một cái dữ liệu bước đầu thôi chứ nó chưa thực sự quá là phức tạp. Trong các cái bài toán phức tạp hơn thì cái tính chất phi tuyến tính và cái tính zízắc của nó nó còn nhiều hơn như thế này nữa. Đây chỉ là một cái tập dữ liệu đơn giản thôi</code>          | <code>ở đây và nó chạm vào những điểm màu xanh thì khoảng cách từ biên trái sang biên phải sẽ gọi là margin và các điểm nằm trên các biên trái và biên phải này là support vector thì đây là hình ảnh để minh họa cho cả 3 khái niệm mà chúng ta đã nói ở trên thế thì đối với dữ liệu, chúng ta sẽ xem xét một tình huống đơn giản trước đó là dữ liệu của mình, nó có một mối quan hệ tuyến tính hay là Linear Data thì đây là dữ liệu có thể phân tách được bởi 1 siêu phẳng thì chúng ta nhìn cái hình này chúng ta thấy một cách trực quan thì chúng ta thấy là có thể phân chia được ra làm 2 phần bằng 1 đường thẳng thì phân lớp SVM trong dữ liệu **tuyến tính** cho tập dữ liệu gồm 2 lớp ví dụ như ở đây chúng ta có 2</code> | <code>hình bên tay trái ở đây chúng ta sẽ thấy là 2 tập là màu xanh và màu cam thì nó sẽ không thể nào có thể chia tách ra được bằng một đường thẳng Ví dụ như chúng ta kẻ một cái đường như thế này hoặc là chúng ta kẻ một cái đường như thế này thì không có cách nào mà có thể chia nó ra làm hai phần không có cách nào để chia nó ra làm hai phần được với một đường thẳng mà chúng ta chỉ có thể là có một cái đường rất là phức tạp như thế này nó sẽ đi len lỏi để mà chia tách nó ra làm hai phần thì đây nó gọi là một cái ví dụ về phân loại dữ liệu nhưng mà nó là phi tuyến Còn ở phía trên đây là một đường thẳng, thì đây chính là tuyến tính Và một đường thẳng thì không thể nào chia tách tập này ra được làm</code> |
  | <code>Những hành động nào trong game có thể tác động trực tiếp đến điểm số mà mình đạt được?</code>                    | <code>cánh tay này xuống hay là giữ nguyên thì đây là 1 cái khớp tay đây là 1 cái khớp tay và phần thưởng đó là cộng 1 tại mỗi lần đứng thẳng và không bị ngã chò chơi Atari thì mục tiêu đó là hoàn thành chò chơi để điểm số của mình là cao nhất và trạng thái của mình là S là dữ liệu pixel thô của trạng thái của trò chơi và hành động của chúng ta là điều khiển trò chơi, ví dụ như là đi qua trái, phải, lên, xuống và phần thưởng của mình là điểm tăng giảm ở mỗi bước của mỗi thời gian Hãy subscribe cho kênh Ghiền Mì Gõ Để không bỏ lỡ những video hấp dẫn</code>                                                                                                                                                   | <code>. Đây là một số thể loại bài toán sử dụng hợp tăng cường Ví dụ ở trên sơ đồ bên đây, chúng ta thấy chơi game thì trạng thái của mình sẽ là vị trí tại các ô chúng ta đang đặt những quân cờ nào rồi action của chúng ta, chúng ta sẽ đi quân cờ nào tiếp theo và phần thưởng cho chúng ta sẽ là cái phản hồi từ cái môi trường đó là cái phần thưởng mà chúng ta đạt được nếu chúng ta đi với cái hành động đó là gì thì đây là cái game cầu vua trong điều khiển robot thì chúng ta sẽ cho biết là cái hành động của các con robot nó sẽ phải làm gì tiếp theo để mà có thể đạt được cái mục tiêu của mình ví dụ như trong cái ví dụ ở đây chúng ta thấy là chúng ta sẽ phải điều khiển các cái hoạt động của cái cánh tay</code> | <code>. một cái hành động tại cái trạng thái đó nó sẽ giúp cho Agent không chỉ nhìn vào những cái phần thưởng ngắn hạn tại vì trong nhiều cái tình huống các cái bài toán nếu như chúng ta chỉ dựa trên cái hành động ngắn hạn thì có thể là kết quả dài hạn của mình nó rất là tệ đặc biệt là trong cái game chơi cờ đúng không ví dụ như đối thủ của mình họ có thể là nhữ cho chúng ta ăn một cái con nào đó nhưng mà sau khi chúng ta ăn xong thì có thể chúng ta sẽ bị chiêu bí do đó thì cái phần thưởng dài hạn sẽ là một cái Kỳ vọng rất là quan trọng để chúng ta cần phải ước lượng và có thể đưa ra những action phù hợp tối ưu Đặc điểm của nó chính là giá trị vài value của trạng thái Giá trị của trạng thái là</code>  | <code>fan tức là chúng ta cho biết hành động của chúng ta là có phanh hay không phanh chiếc xe thì ví dụ như trong game Mario thì chúng ta sẽ có các cái hành động là rời đạt là đi về bên tay trái, đi về tay phải, hoặc là nhảy còn trong cái xe tự lái, ở trong môi trường thực tế thì action của chúng ta sẽ là những cái giá trị liên tục ví dụ như là tốc độ của chúng ta hoặc là lực chúng ta sẽ đạp ga, lực chúng ta sẽ đạp phanh là gì hoặc là các action rời rạt, ví dụ như là quyết định xem là tăng tốc hay là giảm tốc rồi rẽ trái hay là rẽ phải nhưng mà đi kèm với các action rời rạt này thì nó sẽ có các action liên tục ví dụ như là muốn tăng tốc thì tăng tốc bao nhiêu rồi phải đạp ga là bao nhiêu rồi rẽ</code> | <code>lý và với mục tiêu đó là để cân bằng cây xào trên xe đẩy này thì chúng ta sẽ có các trạng thái S trạng thái này nó sẽ cho biết là tại vị trí hiện tại thì cây xào đã tạo một góc theta một góc theta là bao nhiêu so với trục đứng này Mục tiêu là hướng đến để cho theta là 0 để cho cây xào đứng ở giữa Và tốc độ góc và tọa độ xi và vận tốc ngang là trạng thái của cây xào rồi hành động của chúng ta đó là chúng ta sẽ tương tác một cái lực nằm ngang tác động vào cái xe đẩy như thế nào thì đây chính là cái action lưu ý là ở đây chúng ta nhầm đây là action A và cái phần thưởng đó là gì? Cộng 1, nếu tại thời điểm cộng 1, tại mỗi thời điểm cây xào mà thẳng đứng tức là nếu như cây xào đạt được đến trạng</code>  | <code>mà phải chờ 1 khoảng thời gian sau nó mới có thể đưa ra được cái reward thì đây là 2 loại reward khác nhau là immediate hoặc là delay thì đối với cái delay là cái mà có lẽ là xuất hiện phổ biến nhất là vì tại 1 cái action hiện tại thì nhiều khi chúng ta sẽ không thấy được ngay cái reward của mình là gì mà phải chờ sau rất nhiều bước tiếp theo thì chúng ta mới có thể thấy rõ được phần thưởng trả về ví dụ như là reward của mình đó là thắng cả ván cờ thì phải sau rất nhiều bước chúng ta mới thấy được cái reward này thì nếu như chúng ta thắng ván cờ thì rõ ràng cái điểm của mình nó sẽ rất là cao là cộng 100 điểm rồi robot mà va chạm vô một cái chứng ngại vật nào đó thì đó sẽ là bị trừ điểm là</code>  |
  | <code>Cách sử dụng drop_duplicates trong pandas như thế nào để loại bỏ các bản ghi trùng lặp một cách hiệu quả?</code> | <code>. Rồi drop_duplicates. Tức là cái bảng của mình nó sẽ có tình huống là hai cái dòng dữ liệu có giá trị giống nhau thì nó sẽ loại bỏ đi, nó chỉ chừa lại duy nhất một cái một cái dòng thôi. Rồi ngoài ra thì còn rất nhiều những cái hàm khác, ví dụ như là df.head() tức là lấy ra N dòng đầu tiên. Hoặc là df.tail() là lấy ra N dòng cuối cùng. Rồi các cái thao tác trên cột. Ví dụ như đây là cái hàm, đây là cái phương thức để cho chúng ta có thể lấy ra những cái cột. Ví dụ như trong cái bảng này có rất nhiều cột, nhưng mà bây giờ chúng ta đang muốn lọc ra những cái cột màu xanh như thế này thì chúng ta sẽ điền cái tên cột mà chúng ta muốn lấy dữ liệu, ví dụ cột Width, cột Height và cột Species</code> | <code>những cái tính chất nhất quán của dữ liệu rồi chúng ta có thể à thay đi gọi là loại bỏ những cái dữ liệu bị trùng lắp tức là nếu như dữ liệu của mình trùng lắp quá nhiều thì nó cũng ảnh hưởng đến cái hiệu năng của à cái mô hình học máy và chúng ta sẽ drop duplicate chúng ta sẽ loại bỏ đi những cái dữ liệu à Để trùng r đó rồi thay bỏ loại bỏ những cái cột dữ liệu không cần thiết chúng ta lấy ví dụ như có những cái cột dữ liệu mà chúng ta biết trước là nó sẽ không liên quan đến cái việc mà đưa ra cái dự đoán ờ output cuối cùng Ví dụ như cái cột số thứ tự hoặc là cái cột mã nhân viên thì đây là thường là những cái giá trị ngỗ nhiên nó không có đóng góp nhiều cho cái việc mà huấn luyện nên</code>      | <code>. Ví dụ chúng ta thấy ở nguyên một cái bảng như thế này và df['Length'] lớn hơn 7. Tức là trích ra những cái dòng mà nó thỏa mãn cái điều kiện là cái giá trị của một cái cột nào đó, ví dụ cột này là cột Length, cột chiều dài lớn hơn 7. Thì trong số những cái giá trị trong cái cột này, cái cột Length này thì giá trị nào mà lớn hơn 7 thì nó sẽ lấy ra. Ví dụ như ở đây nó có hai dòng này có hai giá trị này là lớn hơn 7 thì nó sẽ pick ra hai dòng. Thì nó sẽ tạo ra là một cái bảng mới bao gồm là hai cái quan sát với cái trường Length của mình là lớn hơn 7. Rồi drop_duplicates</code>                                                                                                                          | <code>. đây là cái hàm lỗi của một mẫu dữ liệu. Và khi này thì mã giả của mình chúng ta sẽ duyệt qua mọi epoch và với mỗi epoch chúng ta sẽ shuffle data của mình. Tức là data của mình sẽ xáo trộn lên, do đó ở đây không phải là data mà là shuffle data. Sau đó thì, for each example, tức là với mỗi một example, thì ở đây chúng ta sẽ lấy ra đúng một mẫu thôi. Và mẫu này là random. Rồi sau đó chúng ta sẽ xác định cái lỗi và sau đó là tính cái gradient, rồi sau đó cập nhật lại cái tham số. Với mỗi một cái lượt này, thì đó là một cái data của mình. Đây sẽ là một cái example. Mỗi example sẽ là một mẫu dữ liệu</code>                                                                                                 | <code>hay không thì đó chính là chúng ta hiểu rõ về cái dữ liệu của mình những cái câu hỏi mà chúng ta cần phải trả lời Bước tiếp theo đó là cái tiền đề để chúng ta có thể làm sạch dữ liệu về sau tại vì khi chúng ta phân tích dữ liệu thì nó sẽ xác định được những cái vấn đề mà dữ liệu của mình đang còn tồn tại ví dụ thiếu dữ liệu có những cái trường thuộc tính trong dữ liệu nó bị chứa giá trị rỗng hoặc là chứa một cái giá trị là không xác định hoặc là trong cái dữ liệu của mình nó bị trùng lập có những cái phần tử gọi là hai hàng giống y chang nhau thì khi hai hàng giống y chang nhau này thì sẽ gây ra cho mình đó là dữ liệu của mình thừa và nếu như cái tình trạng mà trùng lắp dữ liệu này á mà quá</code> | <code>. Và cái mã giả của mình nó sẽ là mini-batch GD là chúng ta sẽ lặp qua số epoch và với mỗi lần lặp, với mỗi epoch thì chúng ta sẽ shuffle data, chúng ta sẽ random dữ liệu. Thì đây sẽ là shuffle data. Rồi sau đó sau khi chúng ta đã shuffle data xong thì chúng ta sẽ lấy một batch, lấy một batch thì chúng ta sẽ có một cái hàm get_batch. Get_batch này nó sẽ chia cái data của mình ra làm nhiều phần. Ví dụ như mỗi cái phần này nó sẽ là một batch. Chúng ta sẽ duyệt qua hết các cái batch trong cái shuffle data này. Bắt đầu chúng ta sẽ train trên dữ liệu này sau đó chúng ta sẽ train trên dữ liệu tiếp theo, cái batch tiếp theo. Sau đó chúng ta sẽ train trên cái phần tiếp theo</code>                         |
* Loss: [<code>CachedMultipleNegativesRankingLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedmultiplenegativesrankingloss) with these parameters:
  ```json
  {
      "scale": 20.0,
      "similarity_fct": "cos_sim",
      "mini_batch_size": 8,
      "gather_across_devices": false
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 64
- `per_device_eval_batch_size`: 64
- `fp16`: True
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `eval_strategy`: no
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 64
- `per_device_eval_batch_size`: 64
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 3
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: {}
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: True
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch  | Step | Training Loss |
|:------:|:----:|:-------------:|
| 1.2690 | 500  | 1.7203        |
| 2.5381 | 1000 | 1.117         |


### Framework Versions
- Python: 3.12.9
- Sentence Transformers: 5.1.2
- Transformers: 4.57.1
- PyTorch: 2.10.0+cu128
- Accelerate: 1.10.1
- Datasets: 4.3.0
- Tokenizers: 0.22.1

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

#### CachedMultipleNegativesRankingLoss
```bibtex
@misc{gao2021scaling,
    title={Scaling Deep Contrastive Learning Batch Size under Memory Limited Setup},
    author={Luyu Gao and Yunyi Zhang and Jiawei Han and Jamie Callan},
    year={2021},
    eprint={2101.06983},
    archivePrefix={arXiv},
    primaryClass={cs.LG}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->