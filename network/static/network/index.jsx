class Post extends React.Component {

	constructor(props) {
		super(props)
	}

    render() {
        return (
	        <div class="row">
				<div class="col-2">
					<span>{this.props.user}</span>
				</div>
				<div class="col-8">
					<span>{this.props.content}</span>
				</div>
				<div class="col-2">
					<span>{this.props.timestamp}</span>
				</div>
			</div>
        )
    }
}

class App extends React.Component {

	constructor(props) {
		super(props)

		this.state = {
			posts: [
				{
					user: 'coolguy',
					timestamp: 'Feb 1st 2021 22:31PM',
					content: 'I am so cool'
				},
				{
					user: 'anothercoolguy',
					timestamp: 'Feb 1st 2021 22:35PM',
					content: 'Yeah you are!'
				}
			]
		}
	}

    render(posts) {
        return (
			this.state.posts.map(post => <Post
				user={post.user}
				timestamp={post.timestamp}
				content={post.content}
			/>)
        )
    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
